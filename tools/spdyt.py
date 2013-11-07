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
usage: %prog [options] <spdy-config.cfg> 
Default spdy version will be 2. 
"""
parser = OptionParser(usage)

#Define the options available
parser.add_option("-2",dest="version",action="store_const",const="2",default=2,help="provide this option for using spdy version 2")
parser.add_option("-3",dest="version",action="store_const",const="3",help="provide this option for using spdy version 2")
parser.add_option("-o","--output",dest="out_file",help="Write output to <file> instead of stdout")
parser.add_option("-i",dest="in_data",action="store_true",default=False,help="print post/put data to console")
parser.add_option("-v", "--verbose-level",dest="debug",help="Decide the level of verbosity from 1-3", default=0)
parser.add_option("-n",dest="no_tls",action="store_true",default=False,help="dont use ssl/tls. Use plain spdy over tcp")
#parser.add_option("-v", "--verbose",action="store_true", dest="verbose", default=False,help="make lots of noise [default is no verbose]")

#Parse the options supplied from CLI
(cmd_options, args) = parser.parse_args()
if not args:
    print("please provide configuration file")
    exit()
CFG_FILE=str(args[0])
debug=int(cmd_options.debug)
print("SPDY configuration will be picked from file:",CFG_FILE)

#initialize zlib
cmd_options.version=int(cmd_options.version)
traffic.inflater = Inflater(cmd_options.version)
traffic.deflater = Deflater(cmd_options.version)
#print(options.url_form_data)
#print(options.form_data)
#print(options.custhdr)
if (cmd_options.out_file):
    outfile=open(cmd_options.out_file,'w')

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
            if side=="request":
                cprint("[ stream %s: Request side syn_reply] send SYN_REPLY frame <version=%s,fin=%s,stream-id=%s>" %(frame.stream_id,frame.version,frame.flags,frame.stream_id),'green')
            else:
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
            if side=="request":
                cprint("[ stream %s: RST] send RST_STREAM frame <version=%s,flags=%s,status=%s>" %(frame.stream_id,frame.version,frame.flags,frame.status_code),'green')
            else:
                cprint("[ stream %s: RST] received RST_STREAM frame <version=%s,flags=%s,status=%s>" %(frame.stream_id,frame.version,frame.flags,frame.status_code),'cyan')

        if frame.type==frames.SETTINGS:
            if side=="request":
                cprint("send SETTINGS frame <version=%s,flags=%s>" %(frame.version,frame.flags),'green')
            else:
                cprint("received SETTINGS frame <version=%s,flags=%s>" %(frame.version,frame.flags),'cyan')

        if frame.type==frames.PING:
            if side=="request":
                cprint("send PING frame <version=%s,flags=%s,ping_id=%s>" %(frame.version,frame.flags,frame.ping_id),'green')	
            else:
                cprint("received PING frame <version=%s,flags=%s,ping_id=%s>" %(frame.version,frame.flags,frame.ping_id),'cyan')

    else: #data frame
        if side=="request":
            if cmd_options.in_data:
                cprint("[ stream %s: Request data ] send data <fin=%s,stream-id=%s,length=%s>" %(frame.stream_id,frame.flags,frame.stream_id,frame.length),'green')
                for i in frame.data.splitlines():
                    print("%30s %s" %('',i))
            else:
                if frame.flags==frames.FLAG_FIN:
                    cprint("[ stream %s: Request data ] last send data <fin=%s,stream-id=%s,length=%s>" %(frame.stream_id,frame.flags,frame.stream_id,frame.length),'green')

        else:
            if cmd_options.out_file:
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

############## Read config file  ################
#################################################
COMMENT_CHAR = '#'
OPTION_CHAR =  '='

################ output ######################
options = {} #contains all the cfg options
hdr_dict_dict={} #Is a dictionary of all header dictionary. dictionarykey name is header file name provided in cfg

############ Default config values #################
options["port"]=443
options["stream_seq"]="1,1"
options["seq1"]="version=2,flag-fin=1,flag-unidirectional=0,stream-id=33"
options["seq2"]="version=2,flag-fin=1,flag-unidirectional=0,stream-id=33"
options["hdr_seq_for_stream"]="1.hdr,1.hdr"

############ Parse the cfg file #####################
cfglist = []
file = open(CFG_FILE, "r")
cfglist=file.readlines()
for cfg_line in cfglist:
    if COMMENT_CHAR in cfg_line:
        continue
    if OPTION_CHAR in cfg_line:
        option, value = cfg_line.split(OPTION_CHAR, 1)
        option = option.strip()
        value = value.strip()
        option=option.lower()
        options[option] = value
file.close()

###################### Arrange the parsed config parameters ########################
options["stream_seq"]=options["stream_seq"].split(",")
options["hdr_seq_for_stream"]=options["hdr_seq_for_stream"].split(",")

tmp_list=[]
i=1
for seq in options["stream_seq"]:
    tmp_list.append(options["seq"+str(i)])
    options.pop("seq"+str(i))
    i=i+1

options["seq_cfg_list_dict"]=[]
i=0
for seq_cfg in tmp_list:
    options["seq_cfg_list_dict"].append({})
    seq_cfg=seq_cfg.strip("{")
    seq_cfg=seq_cfg.strip("}")
    seq_cfg=seq_cfg.split(",")
    for cfg in seq_cfg:
        if "=" in cfg:
            cfg_name,cfg_value=cfg.split("=",1)
            cfg_name.strip()
            cfg_value.strip()
            cfg_name=cfg_name.lower()
            options["seq_cfg_list_dict"][i][cfg_name]=cfg_value
    i=i+1
#print(options)
#print()

#################### Parse the hdr files ####################
for hdr_file in options["hdr_seq_for_stream"]:
    hdr_dict_dict[hdr_file]={}
    file = open(hdr_file,"r")
    hdr_list=file.readlines()
    file.close()
    for hdr_line in hdr_list:
        if COMMENT_CHAR in hdr_line:
            continue
        if ":" in hdr_line:
            hdr_name,hdr_value=hdr_line.split(":",1)
            hdr_name=hdr_name.strip()
            hdr_value=hdr_value.strip()
            hdr_dict_dict[hdr_file][hdr_name]=hdr_value

#print(hdr_dict_dict)   
if (debug > 1):
    print("--------------- Creation of frames as per sequence given in config file - Started-------------")
#print("options is: ", options)
print()
#print("header file sequence is: ", options["hdr_seq_for_stream"])
print("stream_seq is: ",options["stream_seq"])
print("Will be sending",len(options["stream_seq"]),"frames","\n")

c=traffic.mode(cmd_options.version,'client')
out=bytearray()

#generate frames from 
i=0
for stream_seq_frame in options["stream_seq"]:
    #print("parameters for this frame are:")
    cfg_dict=options["seq_cfg_list_dict"][i]
    header_file=options["hdr_seq_for_stream"][i]
    version=int(cfg_dict["version"])
    #print("version: ",version)
    stream_id=int(cfg_dict["stream_id"])
    #print("stream-id: ",stream_id)
    header_dict=hdr_dict_dict[header_file]
    headers=[]
    for key in header_dict.keys():
        headers.append((key,str(header_dict[key])))
    #print("header dict: ",header_dict)
    flag_str=cfg_dict["flag"]
    if stream_seq_frame=="1":
        print("Frame ",i+1,"is a SYS_STREAM frame")
        if flag_str=="FIN":
            flag=frames.FLAG_FIN
        if flag_str=="UNID":
            flag=frames.FLAG_UNID
        if flag_str=="BOTH":
            flag=0x03
        if flag_str=="0":
            flag=frames.FLAG_NULL
        syn_stream_frame=frames.syn_stream_frame(stream_id,headers,flag,version)
        c.put_frame(syn_stream_frame)

    if stream_seq_frame=="2":
        print("Frame ",i+1,"is a SYS_REPLY frame")
        if flag_str=="FIN":
            flag=frames.FLAG_FIN
        if flag_str=="UNID":
            flag=frames.FLAG_UNID
        if flag_str=="BOTH":
            flag=0x03
        if flag_str=="0":
            flag=frames.FLAG_NULL
        syn_reply_frame=frames.syn_reply_frame(stream_id,headers,flag,version)
        c.put_frame(syn_reply_frame)

    if stream_seq_frame=="3":
        print("Frame ",i+1,"is a RST_STREAM frame")
        flag=int(flag_str)
        error_code=int(cfg_dict["error_code"])
        rst_stream_frame=frames.rst_stream_frame(stream_id,error_code,flag,version)
        c.put_frame(rst_stream_frame)

    if stream_seq_frame=="6":
        print("Frame ",i+1,"is a PING frame")
        flag=int(flag_str)
        ping_frame=frames.ping_frame(stream_id,flag,version)
        c.put_frame(ping_frame)

    if stream_seq_frame=="7":
        print("Frame ",i+1,"is a GOAWAY frame")
        flag=int(flag_str)
        goaway_frame=frames.goaway_frame(stream_id,flag,version)
        c.put_frame(goaway_frame)

    if stream_seq_frame=="8":
        print("Frame ",i+1,"is a HEADERS frame")
        flag=int(flag_str)
        header_frame=frames.header_frame(stream_id,headers,flag,version)
        c.put_frame(header_frame)

    if stream_seq_frame=="9":
        print("Frame ",i+1,"is a DATA frame")
        if flag_str=="FIN":
            flag=frames.FLAG_FIN
        if flag_str=="UNID":
            flag=frames.FLAG_UNID
        if flag_str=="BOTH":
            flag=0x03
        if flag_str=="0":
            flag=frames.FLAG_NULL
        dataf=open(cfg_dict["data_file"],"r")
        data=dataf.read()
        data_frame=frames.dataframe(stream_id,data,flag)
        c.put_frame(data_frame)

    i=i+1

#print(c.tx_frames_queue)
if (debug > 1):
    print("--------------- Creation of frames as per sequence given in config file - Completed-------------")


#Socket and final frames
ip=options["ip"]
port=int(options["port"])
npn_str="spdy/"+str(cmd_options.version)
print("=========================================================================")
print("")
cprint("[ session starts ]",'white','on_blue')
print("protocol which will be supported by this client is - %s" %(npn_str))
print("ip is ",ip, "port is", port)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

if not cmd_options.no_tls:
    ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ctx.set_npn_protocols([npn_str])
    ss = ctx.wrap_socket(sock)
    ss.connect((ip,port))
    print("protocol selected by npn negotiation is : %s" %(ss.selected_npn_protocol()))
else:
    sock.connect((ip,port))
    ss=sock
    print("protocol selected is plain spdy over tcp")

if (debug > 0):
    for frame in c.tx_frames_queue:
        print_frame(frame,"request")

#sending/receiving the frames
while True:
    out=c.controlled_outgoing()
    if out:
        ss.sendall(out)
    data=ss.recv(1024)
    c.incoming(data)
    while True:
        frame=c.get_frame()
        if frame:
            if (debug > 0):
                if frame.is_control==0 and cmd_options.out_file:
                    outfile=open(cmd_options.out_file,'a') #to save from memory error we will be closing the file and opening it again for each write
                print_frame(frame)
            elif cmd_options.out_file and frame.is_control==0:
                outfile=open(cmd_options.out_file,'a')
                print_frame(frame)
            c.controlled_incoming(frame) 
        else:
            break

    l=list(c.stream_state.values())
    k=list(c.stream_state.keys())

    if len(l)==(l.count('close')+l.count('terminate')):
        cprint("[ Final status ]",'white','on_blue')
        print("state of all the streams is: ",c.stream_state)
        print("")
        ss.close()
        break


