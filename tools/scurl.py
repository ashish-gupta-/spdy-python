#!/usr/local/bin/python
from optparse import OptionParser
import spdylib.frames as frames
import spdylib.traffic as traffic
import re
import socket
import ssl
from termcolor import colored, cprint
from spdylib._zlib_stream import Inflater, Deflater

################################################################################################
############### describe available options and parse them  #####################################
################################################################################################
usage="""
usage: %prog [options] {https://10.102.116.64/testsite/file1k.html,https://10.102.116.64/tesiste/file5.html}"
Default spdy version will be 2 and http version will be 1.1
"""
parser = OptionParser(usage)

#Define the options available
parser.add_option("-H","--header",dest="custhdr",
                    action="append",help="Provide a custom header which will be sent along with the request i.e. -H 'host:10.102.116.64'")
parser.add_option("-2",dest="version",action="store_const",const="2",default=2,help="provide this option for using spdy version 2")
parser.add_option("-3",dest="version",action="store_const",const="3",help="provide this option for using spdy version 2")
parser.add_option("-A","--user-agent",dest="u_agent",default="spdy-curl-v1.0",help="(HTTP) Specify the User-Agent string to send to the HTTP server")
parser.add_option("-F","--form",dest="form_data",help="(HTTP) This lets curl emulate a filled-in form in which a user has pressed the submit button. This causes curl to POST data using the Content-Type multipart/form-data according to RFC 2388. -F data=@file.html for using a file content and -F dump=asasadad for sending specified data on console.")
parser.add_option("-d","--data",dest="url_form_data",
                    action="append",help="(HTTP) Sends the specified data in a POST request to the HTTP server, in the same way that a browser does when a user has filled in an HTML form and presses the submit button. This will cause curl to pass the data to the server using the content-type application/x-www-form-urlencoded")
parser.add_option("-L","--location",dest="loc",action="store_true",default=False,help="(HTTP/HTTPS) If the server reports that the requested page has moved to a different location (indicated with a Location: header and a 3XX response code), this option will make scurl redo the request on the new place")
parser.add_option("-o","--output",dest="out_file",help="Write output to <file> instead of stdout")
parser.add_option("-i",dest="in_data",action="store_true",default=False,help="print post/put data to console")
parser.add_option("-n",dest="no_tls",action="store_true",default=False,help="dont use ssl/tls. Use plain spdy over tcp")
parser.add_option("-q",dest="use_def_hdr",action="store_false",default=True,help="do not use default headers. use this option when all the headers have to supplied by user. automatically added headers would be content-type and content-length in case of post and put.")
parser.add_option("-T","--upload-file",dest="put_data",help="This transfers the specified local file to the remote URL using PUT request")
#parser.add_option("-X","--request",dest="req",help="(HTTP) Specifies a custom request method to use when communicating with the HTTP server. The specified request will be used instead of the method otherwise used (which defaults to GET). Support HEAD,DELETE,CUSTOM,TRACE")
parser.add_option("--http-version",dest="http_ver",default="1.1",help="(HTTP) Which HTTP version to use")
parser.add_option("-v", "--verbose",action="store_true", dest="verbose", default=False,help="make lots of noise [default is no verbose]")

#Parse the options supplied from CLI
(options, args) = parser.parse_args()
urls=args
#initialize zlib
options.version=int(options.version)
traffic.inflater = Inflater(options.version)
traffic.deflater = Deflater(options.version)
#print(options.url_form_data)
#print(options.form_data)
#print(options.custhdr)
if (options.http_ver=="1.1"):
    http_string="HTTP/1.1"
else:
    http_string="HTTP/1.0"

if (options.out_file):
    outfile=open(options.out_file,'w')

if (options.use_def_hdr):
    if (options.version==2):
        default_headers={
            'method':'GET',
            'scheme':'HTTP',
            'version':http_string,
            'user-agent':options.u_agent,
            'accept':'*/*',
            }
    if (options.version==3):
        default_headers={
            ':method':'GET',
            ':scheme':'HTTP',
            ':version':http_string,
            'user-agent':options.u_agent,
            'accept':'*/*',
            }

else:
    default_headers={}


###################################################################################################
###################################################################################################
#print(urls)
#print(options.http_ver)
#print(options.custhdr)

#Defining default headers to sent along with the request

def print_frame(frame,side="response"): #print the results on console
    if frame.is_control:
        if frame.type==frames.SYN_STREAM:
            cprint("[ stream %s: Request headers ] send SYN_STREAM frame <version=%s,fin=%s,stream-id=%s,pri=%s>" %(frame.stream_id,frame.version,frame.flags,frame.stream_id,frame.pri),'green')
            for (hname,hvalue) in frame.headers:
                print("%30s %s:%s" %('',hname,hvalue))

        if frame.type==frames.SYN_REPLY:
            cprint("[ stream %s: Response headers ] receive SYN_REPLY frame <version=%s,fin=%s,stream-id=%s>" %(frame.stream_id,frame.version,frame.flags,frame.stream_id),'cyan')
            for (hname,hvalue) in frame.headers:
                print("%30s %s:%s" %('',hname,hvalue))

        if frame.type==frames.GOAWAY:
            if side=="request":
                cprint("[ session closes ]",'white','on_blue')
                cprint("send GOAWAY frame <version=%s,flags=%s,last-good-stream-id=%s>" %(frame.version,frame.flags,frame.last_stream_id),'green')
            else:
                cprint("received GOAWAY frame <version=%s,flags=%s,last-good-stream-id=%s>" %(frame.version,frame.flags,frame.last_stream_id),'cyan')
        
        if frame.type==frames.RST_STREAM:
            cprint("[ stream %s: RST] received RST_STREAM frame <version=%s,flags=%s,status=%s>" %(frame.stream_id,frame.version,frame.flags,frame.status_code),'cyan')

        if frame.type==frames.SETTINGS:
            cprint("received SETTINGS frame <version=%s,flags=%s>" %(frame.version,frame.flags),'cyan')

        if frame.type==frames.PING:
            cprint("received PING frame <version=%s,flags=%s.ping_id=%s>" %(frame.version,frame.flags.frame.ping_id),'cyan')

    else: #data frame
        if side=="request":
            if options.in_data:
                cprint("[ stream %s: Request data ] send data <fin=%s,stream-id=%s,length=%s>" %(frame.stream_id,frame.flags,frame.stream_id,frame.length),'green')
                for i in frame.data.splitlines():
                    print("%30s %s" %('',i))
            else:
                if frame.flags==frames.FLAG_FIN:
                    cprint("[ stream %s: Request data ] last send data <fin=%s,stream-id=%s,length=%s>" %(frame.stream_id,frame.flags,frame.stream_id,frame.length),'green')

        else:
            if options.out_file:
                #cprint("data is dumped into %s file" %(options.out_file),'cyan')
                outfile.write(frame.data)
                outfile.close()
                if frame.flags==frames.FLAG_FIN:
                    cprint("[ stream %s: Response data ] last received data frame <fin=%s,stream-id=%s,length=%s>" %(frame.stream_id,frame.flags,frame.stream_id,frame.length),'cyan')
                    outfile.close()
            else:
                cprint("[ stream %s: Response data ] received data <fin=%s,stream-id=%s,length=%s>" %(frame.stream_id,frame.flags,frame.stream_id,frame.length),'cyan')
                for i in frame.data.splitlines():
                    print("%30s %s" %('',i))
                    

def handle_url_form_data(param):
    data=""
    for i in param:
        if i.find("@")==0: #this is the file name
            fname=i[1:]
            f=open(fname,'r')
            data=data+f.read()+'&'
            f.close()
        else:
            data=data+i+'&'
    return data[0:-1]

def handle_form_data(param):
    data='''----------------------------402bda0d4395\r\n'''
    data=data+'''Content-Disposition: form-data; name="'''
    data=data+param.split('=')[0]+'''"'''
    i=param.split('=')[1]
    if i.find("@")==0: #this is the file name
        fname=i[1:]
        data=data+'''; filename="'''
        data=data+fname+'''"\r\n'''
        data=data+'''Content-Type: text/html\r\n\r\n'''
        fname=i[1:]
        f=open(fname,'r')
        data=data+f.read()+'''----------------------------402bda0d4395\r\n'''
        f.close()
    else:
        data=data+'''\r\nContent-Type: text/html\r\n\r\n'''
        data=data+i+'''\r\n----------------------------402bda0d4395\r\n'''
    return data

def handle_data_frame(data,c):
    x=len(data)/7000
    if(x>1):
        st=0
        en=7000
        flag=frames.FLAG_NULL
        while(x>0):
            data_frame=frames.dataframe(c.stream_id,data[st:en],flag)
            c.put_frame(data_frame)
            x=x-1
            if(x>1):
                st=en
                en=en+7000
            else:
                st=en
                en=(len(data)+1)
                flag=frames.FLAG_FIN
    else:
        data_frame=frames.dataframe(c.stream_id,data,frames.FLAG_FIN)
        c.put_frame(data_frame)

def handle_redirect(frame):
    headers=[]
    hdr_dict=default_headers
    if frame.is_control:
        if frame.type==frames.SYN_REPLY:
            if (options.version==2):
                code=dict(frame.headers)['status']
            if (options.version==3):
                code=dict(frame.headers)[':status']
            if code=='300' or code=='301' or code=='302':
                cprint("Got a 3xx response, redirect request will be sent",'green')
                try:
                    url=dict(frame.headers)['Location']
                except KeyError:
                    url=dict(frame.headers)['location']
                p=r'(http://|https://)?(\S+)'
                url=re.match(p,url).group(2)
                if url.find("/") != -1  :
                    (host,path)=url.split("/",1)
                else:
                    host=url
                    path=""
                if (options.version==2):
                    hdr_dict['host']=host
                    hdr_dict['url']='/'+path
                if (options.version==3):
                    hdr_dict[':host']=host
                    hdr_dict[':path']='/'+path
                
                for key in hdr_dict.keys():
                    headers.append((key,str(hdr_dict[key])))
                redir_frame=frames.syn_stream_frame(c.stream_id,headers,frames.FLAG_FIN,options.version)
                return redir_frame
    return False


header_list=[] #list of list.each component list will contain headers for 1 request 
#Constructing headers for each request
for url in urls:
    headers=[] #list of tuples
    hdr_dict=default_headers
    p=r'(http://|https://)?(\S+)'
    url=re.match(p,url).group(2)
    if url.find("/") != -1  :
        (host,path)=url.split("/",1)
    else:
        host=url
        path=""
    ip=host
    if options.use_def_hdr:
        if (options.version==2):
            hdr_dict['host']=host
            hdr_dict['url']='/'+path
        if (options.version==3):
            hdr_dict[':host']=host
            hdr_dict[':path']='/'+path

    #Convery dict to list of tiple
    if options.url_form_data:
        if options.use_def_hdr:
            if (options.version==2):
                hdr_dict['method']="POST"
            if (options.version==3):
                hdr_dict[':method']="POST"
        hdr_dict['content-type']="application/x-www-form-urlencoded"
        url_data=handle_url_form_data(options.url_form_data)
        hdr_dict['content-length']=len(url_data)

    if options.form_data:
        if options.use_def_hdr:
            if (options.version==2):
                hdr_dict['method']="POST"
            if (options.version==3):
                hdr_dict[':method']="POST"
        hdr_dict['content-type']="multipart/form-data; boundary=----------------------------402bda0d4395"
        final_form_data=handle_form_data(options.form_data)
        hdr_dict['content-length']=len(final_form_data)

    if options.put_data:
        if options.use_def_hdr:
            hdr_dict[':method']="PUT"
        f=open(options.put_data)
        final_put_data=f.read()
        f.close()
        hdr_dict['content-length']=len(final_put_data)

    for key in hdr_dict.keys():
        headers.append((key,str(hdr_dict[key])))
    if options.custhdr:
        for h in options.custhdr:
            (hname,hvalue)=h.split(":")
            headers.append((hname,hvalue))

    header_list.append(headers)

#Socket and final frames
port=443
if options.no_tls:
    port=80
npn_str="spdy/"+str(options.version)
print("=========================================================================")
print("")
cprint("[ session starts ]",'white','on_blue')
print("protocol which will be supported by this client is - %s" %(npn_str))
print("ip is ",ip, "port is", port)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
if not options.no_tls:
    ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ctx.set_npn_protocols([npn_str])
    ss = ctx.wrap_socket(sock)
    ss.connect((ip,port))
    print("protocol selected by npn negotiation is : %s" %(ss.selected_npn_protocol()))
else:
    sock.connect((ip,port))
    ss=sock
    print("protocol selected is plain spdy over tcp")

c=traffic.mode(options.version,'client')
out=bytearray()

#generate frames from the list of headers
for headers in header_list:
    if options.url_form_data:
        syn_stream_frame=frames.syn_stream_frame(c.stream_id,headers,frames.FLAG_NULL,options.version)
        c.put_frame(syn_stream_frame)
        handle_data_frame(url_data,c)
    elif options.form_data:
        syn_stream_frame=frames.syn_stream_frame(c.stream_id,headers,frames.FLAG_NULL,options.version)
        c.put_frame(syn_stream_frame)
        handle_data_frame(final_form_data,c)
    elif options.put_data:
        syn_stream_frame=frames.syn_stream_frame(c.stream_id,headers,frames.FLAG_NULL,options.version)
        c.put_frame(syn_stream_frame)
        handle_data_frame(final_put_data,c)

    else:
        syn_stream_frame=frames.syn_stream_frame(c.stream_id,headers,frames.FLAG_FIN,options.version)
        c.put_frame(syn_stream_frame)
    c.next_stream_id()

#print(c.tx_frames_queue)
#sending/receiving the frames
if options.verbose:
    for frame in c.tx_frames_queue:
        print_frame(frame,"request")

while True:
    redir_status=0
    out=c.controlled_outgoing()
    if out:
        ss.sendall(out)
    data=ss.recv(1024)
    c.incoming(data)
    while True:
        frame=c.get_frame()
        if frame:
            if options.verbose:
                if frame.is_control==0 and options.out_file:
                    outfile=open(options.out_file,'a') #to save from memory error we will be closing the file and opening it again for each write
                print_frame(frame)
            elif options.out_file and frame.is_control==0:
                outfile=open(options.out_file,'a')
                print_frame(frame)
            c.controlled_incoming(frame)
            if options.loc:
                redir_frame=handle_redirect(frame)
                if redir_frame:
                    c.put_frame(redir_frame)
                    c.next_stream_id()
                    print_frame(redir_frame)
                    redir_status=1
        else:
            break
    
    l=list(c.stream_state.values())
    k=list(c.stream_state.keys())

#graceful connection close
    if len(l)==(l.count('close')+l.count('terminate')) and redir_status==0:
        goaway_frame=frames.goaway_frame(k[len(k)-1],frames.FLAG_NULL,options.version)
        print_frame(goaway_frame,"request")
        out=traffic.encode_frame(goaway_frame)
        if out:
            ss.sendall(out)
        data=ss.recv(1024)
        c.incoming(data)
        frame=c.get_frame()
        if frame:
            print_frame(frame)
            cprint("[ Final status ]",'white','on_blue')
            print("state of all the streams is: ",c.stream_state)
            print("")
       #print(c.rx_stream_frames)
        ss.close()
        break







