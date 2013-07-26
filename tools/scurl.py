from optparse import OptionParser
import spdylib.frames as frames
import spdylib.traffic as traffic
import re
import socket
import ssl

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
parser.add_option("-F","--form",dest="from_data",help="(HTTP) This lets curl emulate a filled-in form in which a user has pressed the submit button. This causes curl to POST data using the Content-Type multipart/form-data according to RFC 2388")
parser.add_option("-d","--data",dest="url_data",help="(HTTP) Sends the specified data in a POST request to the HTTP server, in the same way that a browser does when a user has filled in an HTML form and presses the submit button. This will cause curl to pass the data to the server using the content-type application/x-www-form-urlencoded")
parser.add_option("-L","--location",dest="loc",action="store_true",default=False,help="(HTTP/HTTPS) If the server reports that the requested page has moved to a different location (indicated with a Location: header and a 3XX response code), this option will make scurl redo the request on the new place")
parser.add_option("-o","--output",dest="out_file",help="Write output to <file> instead of stdout")
parser.add_option("-T","--upload-file",dest="put_data",help="This transfers the specified local file to the remote URL using PUT request")
parser.add_option("-X","--request",dest="req",help="(HTTP) Specifies a custom request method to use when communicating with the HTTP server. The specified request will be used instead of the method otherwise used (which defaults to GET). Support HEAD,DELETE,CUSTOM,TRACE")
parser.add_option("--http-version",type='int',dest="http_ver",default=1.1,help="(HTTP) Which HTTP version to use")

#Parse the options supplied from CLI
(options, args) = parser.parse_args()
urls=args
print(urls)
print(options.http_ver)
print(options.custhdr)

#Defining default headers to sent along with the request
if (options.http_ver==1.1):
    http_string="HTTP/1.1"
else:
    http_string="HTTP/1.0"

header_list=[]

default_headers={
        'method':'GET',
        'scheme':'HTTP',
        'version':http_string,
        'user-agent':options.u_agent,
        'accept':'*/*',
        }
#Constructing headers for each request
for url in urls:
    headers=[]
    hdr_dict=default_headers
    p=r'(http://|https://)?(\S+)'
    url=re.match(p,url).group(2)
    (host,path)=url.split("/",1)
    ip=host
    hdr_dict['host']=host
    hdr_dict['url']='/'+path

    #Convery dict to list of tiple
    for key in hdr_dict.keys():
        headers.append((key,hdr_dict[key]))
    if options.custhdr:
        for h in options.custhdr:
            (hname,hvalue)=h.split(":")
            headers.append((hname,hvalue))
    header_list.append(headers)


#Socket and final frames
print("ip is",ip)
port=443
npn_str="spdy/"+str(options.version)
print("npn str is",npn_str)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
ctx.set_npn_protocols([npn_str])
ss = ctx.wrap_socket(sock)
ss.connect((ip,port))

c=traffic.mode(options.version,'client')
out=bytearray()
for headers in header_list:
    syn_stream_frame=frames.syn_stream_frame(c.stream_id,headers)
    c.put_frame(syn_stream_frame)
    c.next_stream_id()

while True:
    out=c.controlled_outgoing()
    print(c.stream_state)
    print(c.rx_stream_frames)
    if out:
        ss.sendall(out)
    data=ss.recv(1024)
    c.incoming(data)
    while True:
        frame=c.get_frame()
        if frame:
            c.controlled_incoming(frame)
        else:
            break
    
    l=list(c.stream_state.values())
    k=list(c.stream_state.keys())
    print(c.stream_state)
    print(c.rx_stream_frames)
    if len(l)==(l.count('close')+l.count('terminate')):
        goaway_frame=frames.goaway_frame(k[len(k)-1])
        break















