import spdylib.frames as frames
from bitarray import bitarray
from spdylib._zlib_stream import Inflater, Deflater

version=2
inflater = Inflater(version)
deflater = Deflater(version)

class ClientError(Exception):
    #to handle error in client side code
    pass

class SpdyProtocolError(Exception):
    #Spdy protocol issue
    pass

def _value_to_bits(value,no_of_bits): #Converting an integer to bitarray of size 'no_of_bits' 
    final=bitarray()
    binary_value=bin(value)[2:]
    bits=bitarray(binary_value)
    chunk=bitarray(no_of_bits-len(bits))
    chunk.setall(0)
    final.extend(chunk)
    final.extend(bits)
    return final

def _bits_to_value(bits): #Convert bitarray to int
    final=bits
    final.reverse()
    final.fill()
    final.reverse()
    in_bytes=final.tobytes()
    value=int.from_bytes(in_bytes,'big')
    return value

def _parse_headers(chunk,version):
    headers=[]
    """
        +------------------------------------+
        | Number of Name/Value pairs (int16) |
        +------------------------------------+
        |     Length of name (int16)         |
        +------------------------------------+
        |           Name (string)            |
        +------------------------------------+
        |     Length of value  (int16)       |
        +------------------------------------+
        |          Value   (string)          |
        +------------------------------------+
        |           (repeats)                |
    """
    chunk=inflater.decompress(chunk)
    if version==2:
        size=2
    else:
        size=4
    num_of_headers=int.from_bytes(chunk[0:size],'big')
    curser=size
    for i in range(num_of_headers):
        #decode header name
        len_hname=int.from_bytes(chunk[curser:(curser+size)],'big')
        curser=curser+size
        hname=chunk[curser:(len_hname+curser)].decode('utf-8')
        curser=curser+len_hname

        #decode header value
        len_hvalue=int.from_bytes(chunk[curser:(curser+size)],'big')
        curser=curser+size
        hvalue=chunk[curser:(len_hvalue+curser)].decode('utf-8')
        curser=curser+len_hvalue

        #inserting header name and value to output array
        headers.append((hname,hvalue))
    
    return headers

def parse_frame(chunk):
    #Checking sufficient length of frame for decoding purposes
    if(len(chunk)<8):
        return (False,chunk)
    data_length=int.from_bytes(chunk[5:8],'big')
    last_byte_for_frame=8+data_length
    if(len(chunk)<(data_length+8)):
        return (False,chunk)
   

    #Decoding the frame
    tmp_bits=bitarray()
    tmp_bits.frombytes(bytes(chunk[0:4]))
    if (tmp_bits[0]==True): #it is control frame
        tmp_bits[0]=0

        #Decoding general control frame fields
        tmp_chunk=tmp_bits.tobytes()
        version=int.from_bytes(tmp_chunk[0:2],'big')
        type=int.from_bytes(tmp_chunk[2:4],'big')
        flags=int.from_bytes(chunk[4:5],'big')

        #Initialize a frame object
        if(type==1):
            frame=frames.syn_stream_frame(1,[],flags,version)
        elif(type==2):
            frame=frames.syn_reply_frame(1,[],flags,version)
        elif(type==3):
            frame=frames.rst_stream_frame(1,1,flags,version)
        elif(type==4):
            frame=frames.settings_frame([],flags,version)
        elif(type==5):
            frame=frames.noop_frame(flags,version)
        elif(type==6):
            frame=frames.ping_frame(1,flags,version)
        elif(type==7):
            frame=frames.goaway_frame(1,flags,version)
        elif(type==8):
            frame=frames.header_frame(1,[],flags,version)
        else:
            return -1

        #Find out frame parameters using frame definition
        frame_definition=frame._definition
        print(frame_definition)
        bits=bitarray()
        bits.frombytes(bytes(chunk[8:last_byte_for_frame]))
        curser=0
        for (attr,num_bits) in frame_definition:
            if(attr==0) or (attr==1):
                curser=curser+num_bits
            elif(attr=='headers'):
                header_bytes=bits[curser:].tobytes()
                frame.headers=_parse_headers(header_bytes,version)
            elif(attr=='id_pairs'):
                pass
            else:
                attr_value=_bits_to_value(bits[curser:(num_bits+curser)])
                setattr(frame,attr,attr_value)
                curser=curser+num_bits

        return (True,chunk[last_byte_for_frame:],frame)
            
    else : #it is a data frame
        stream_id=int.from_bytes(chunk[0:4],'big')
        flags=int.from_bytes(chunk[4:5],'big')
        data=chunk[8:last_byte_for_frame].decode('utf-8')
        frame=frames.dataframe(stream_id,data,flags)
        return (True,chunk[last_byte_for_frame:],frame)


def _encode_headers(headers,version):
    out=bytearray()
    if version==2:
        """
        +------------------------------------+
        | Number of Name/Value pairs (int16) |
        +------------------------------------+
        |     Length of name (int16)         |
        +------------------------------------+
        |           Name (string)            |
        +------------------------------------+
        |     Length of value  (int16)       |
        +------------------------------------+
        |          Value   (string)          |
        +------------------------------------+
        |           (repeats)                |
        """

        num_of_headers=len(headers)
        out.extend(num_of_headers.to_bytes(2,'big'))
        for (hname,hvalue) in headers:
            #Convert header name and value to utf-8 encoded bytes
            e_hname=bytes(hname,'utf-8')
            e_hvalue=bytes(hvalue,'utf-8')

            #Insert the header name and its length
            out.extend(len(e_hname).to_bytes(2,'big'))
            out.extend(e_hname)

            #Insert the header value and its length
            out.extend(len(e_hvalue).to_bytes(2,'big'))
            out.extend(e_hvalue)

    if version==3:
        """
        +------------------------------------+  
        | Number of Name/Value pairs (int32) |   <+
        +------------------------------------+    |
        |     Length of name (int32)         |    | This section is the "Name/Value
        +------------------------------------+    | Header Block", and is compressed.
        |           Name (string)            |    |
        +------------------------------------+    |
        |     Length of value  (int32)       |    |
        +------------------------------------+    |
        |          Value   (string)          |    |
        +------------------------------------+    |
        |           (repeats)                |   <+
        """

        num_of_headers=len(headers)
        out.extend(num_of_headers.to_bytes(4,'big'))
        for (hname,hvalue) in headers:
            #Convert header name and value to utf-8 encoded bytes
            e_hname=bytes(hname,'ascii')
            e_hvalue=bytes(hvalue,'ascii')

            #Insert the header name and its length
            out.extend(len(e_hname).to_bytes(4,'big'))
            out.extend(e_hname)

            #Insert the header value and its length
            out.extend(len(e_hvalue).to_bytes(4,'big'))
            out.extend(e_hvalue)

    return deflater.compress(bytes(out))

def encode_frame(frame): #Converting the frame into bytes using the frame definition
    encoded_frame=bytearray() 
    if frame.is_control:
        is_header=0
        #Handling common control frame fields
        tmp=bitarray()
        tmp.extend(b'1') #control bit
        tmp.extend(_value_to_bits(frame.version,15))
        tmp.extend(_value_to_bits(frame.type,16))
        tmp.extend(_value_to_bits(frame.flags,8))
        print("control frame headers are:",tmp)
        
        #Handling fields in control frame types i.e. syn stream, rst stream etc
        frame_definition=frame._definition
        bits=bitarray()
        for (value,num_bits) in frame_definition:
            if(type(value)==bool):
                in_bits=bitarray(num_bits)
                in_bits.setall(value)
                bits.extend(in_bits)

            elif(value=='id_pairs'):
                pass

            elif(value=='headers'):
                is_header=1

            else:
                frame_attr=getattr(frame,value)
                in_bits=_value_to_bits(frame_attr,num_bits)
                bits.extend(in_bits)
        data=bits.tobytes()
        data=bytearray(data)
        print("syn stream specific headers except http headers are:", data)
        if is_header:
            encoded_headers=_encode_headers(frame.headers,frame.version)
            data.extend(encoded_headers)
        
        data_length=len(data)
        print("length of syn stream payload is:", data_length)
        tmp.extend(_value_to_bits(data_length,24))
        encoded_frame.extend(tmp.tobytes())
        print("encoded frame for control frame specif headers is:",encoded_frame)
        encoded_frame.extend(data)
        print("encoded frame is:",encoded_frame)

    else: #data frame

        tmp=bitarray()

        tmp.extend(b'0') #cpntrol bit
        tmp.extend(_value_to_bits(frame.stream_id,31))
        tmp.extend(_value_to_bits(frame.flags,8))
        tmp.extend(_value_to_bits(len(frame.data),24))
        encoded_frame.extend(tmp.tobytes())
        encoded_frame.extend(bytes(frame.data,'utf-8'))

    return encoded_frame

class mode(object):
    def __init__(self,version=2,endpoint_mode='client'):
        self.version=version
        self.endpoint_mode=endpoint_mode
        if(endpoint_mode=='client'):
            self.stream_id=1
            self.ping_id=1
        else:
            self.stream_id=2
            self.ping_id=2
        self.stream_state={} #This will hold latest state of all the streams. State of a stream can be start, client_close, server_close, terminate,close
        self.rx_stream_frames={} #This will hold all the received frames associated with all active(start,client_close,server_close) streams
        self.tx_frames_queue=[] #This will hold all frames which have to be transmitted
        self.rx_extra_frames=[] #spdy layer related frames i.e. settings, goaway etc.
        self.in_buffer=bytearray()

    def next_stream_id(self):
        self.stream_id=self.stream_id+2

    def next_ping_id(self):
        self.ping_id=self.ping_id+2

    def put_frame(self,frame):
        self.tx_frames_queue.append(frame)

    def incoming(self,data):
        self.in_buffer.extend(data)

    def get_frame(self): #Pull out frames from the in_buffer
        tmp=parse_frame(self.in_buffer)
        if(tmp[0]==False): #no enough bytes to pull out frame information
            return False
        else:
            self.in_buffer=tmp[1]
            frame=tmp[2]
            return frame

    def controlled_incoming(self,frame):
        if frame.is_control:
            if (frame.type==frames.SYN_REPLY):
                if frame.stream_id not in self.stream_state: #clienthas received a data frame for a stream id which does not exist
                    raise SpdyProtocolError("stream id for this syn_reply frame does not exist: server has sent a wrong syn_reply frame")
                else: #stream id exists
                    self.rx_stream_frames[frame.stream_id].append(frame)
                    if(frame.flags==frames.FLAG_FIN):
                        self.stream_state[frame.stream_id]='close'
                
            if (frame.type==frames.RST_STREAM):
                if frame.stream_id not in self.stream_state: #clienthas received a data frame for a stream id which does not exist
                    raise SpdyProtocolError("stream id for this syn_reply frame does not exist: server has sent a wrong syn_reply frame")
                else:
                    self.rx_stream_frames[frame.stream_id].append(frame)
                    self.stream_state[frame.stream_id]="terminate"

            if (frame.type==frames.HEADERS):
                self.rx_stream_frames[frame.stream_id].append(frame)
            
            if (frame.type==frames.PING):
                self.rx_extra_frames.append(frame)

            if (frame.type==frames.SETTINGS):
                self.rx_extra_frames.append(frame)

            if (frame.type==frames.NOOP):
                self.rx_extra_frames.append(frame)
            
            if (frame.type==frames.GOAWAY):
                self.rx_extra_frames.append(frame)
                return -1


        else: #data frame
            if frame.stream_id not in self.stream_state: #clienthas received a data frame for a stream id which does not exist
                raise SpdyProtocolError("stream id for this data frame does not exist: server has sent a wrong data frame")
            else: #stream exists
                if self.stream_state[frame.stream_id] in ['start','client_close','server_close']: #if stream is still active
                    self.rx_stream_frames[frame.stream_id].append(frame)
                    if (frame.flags==frames.FLAG_FIN): #if this is the last frame on this stream then close the stream
                        self.stream_state[frame.stream_id]="close"



    def controlled_outgoing(self): #follow protocol properly
        out=bytearray()
        while(len(self.tx_frames_queue)>0):
            frame=self.tx_frames_queue.pop(0)
            if frame.is_control: #Control frame
                if (frame.type==frames.SYN_STREAM):
                    out.extend(encode_frame(frame))
                    self.stream_state[frame.stream_id]='start'
                    if(frame.flags==frames.FLAG_FIN):
                        self.stream_state[frame.stream_id]='client_close'
                    self.rx_stream_frames[frame.stream_id]=[]

                if (frame.type==frames.RST_STREAM):
                    out.extend(encode_frame(frame))
                    self.stream_state[frame.stream_id]='terminate'

                if (frame.type==frames.PING):
                    out.extend(encode_frame(frame))

                if (frame.type==frames.HEADERS):
                    out.extend(encode_frame(frame))
                    if(frame.flags==frames.FLAG_FIN):
                        self.stream_state[frame.stream_id]='client_close'

                if (frame.type==frames.SETTINGS) or (frame.type==frames.NOOP) or (frame.type==frames.GOAWAY):
                    out.extend(encode_frame(frame))

            else: #data frame
                if frame.stream_id not in self.stream_state: #if stream has not been created yet, drop the data frame
                    raise ClientError("This data frame belongs to a stream which is not yet created")
                else: #stream is in existance
                    if self.stream_state[frame.stream_id] in ['start','client_close','server_close']: #if stream is still active
                        out.extend(encode_frame(frame))
                        if (frame.flags==frames.FLAG_FIN): #if this is the last frame on this stream then close the stream
                            self.stream_state[frame.stream_id]="close"
        return out





























    


