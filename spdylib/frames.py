
#spdy version to use
DEFAULT_VERSION=2
supported_version=[2,3]

#flags to use in control and data frames
FLAG_FIN = 0x01
FLAG_UNID = 0x02
FLAG_NULL=0x00

#Types of frames
SYN_STREAM=1
SYN_REPLY=2
RST_STREAM=3
SETTINGS=4
NOOP=5
PING=6
GOAWAY=7
HEADERS=8


##############Status codes for rst stream################
#########################################################
PROTOCOL_ERROR=1 #This is a generic error, and should only be used if a more specific error is not available. The receiver of this error will likely abort the entire session and possibly return an error to the user.
INVALID_STREAM=2 #should be returned when a frame is received for a stream which is not active. The receiver of this error will likely log a communications error.
REFUSED_STREAM=3 #This is error indicates that the stream was refused before any processing has been done on the stream.  This means that request can be safely retried.
UNSUPPORTED_VERSION=4 #Indicates that the receiver of a stream does not support the SPDY version requested.
CANCEL=5 #Used by the creator of a stream to indicate that the stream is no longer needed.
INTERNAL_ERROR=6 #The endpoint processing the stream has encountered an error.
FLOW_CONTROL_ERROR=7 #The endpoint detected that its peer violated the flow control protocol.
#Note:  0 is not a valid status code for a RST_STREAM
#status codes only for version 3
STREAM_IN_USE=8
STREAM_ALREADY_CLOSED=9
INVALID_CREDENTIALS=10
FRAME_TOO_LARGE=11
######################################
######################################
class frame(object):
    pass

class dataframe(frame):
    """
    +----------------------------------+
    |0|       Stream-ID (31bits)       |
    +----------------------------------+
    | Flags (8)  |  Length (24 bits)   |
    +----------------------------------+
    |               Data               |
    +----------------------------------+
    """
    def __init__(self,stream_id,data,flags=FLAG_FIN):
        self.stream_id=stream_id
        self.flags=flags
        self.data=data
        self.length=len(data)
        self.is_control=0

class controlframe(frame):
    """
     +----------------------------------+
     |C| Version(15bits) | Type(16bits) |
     +----------------------------------+
     | Flags (8)  |  Length (24 bits)   |
     +----------------------------------+
     |               Data               |
     +----------------------------------+
     """
     
    def __init__(self,type,flags,version=DEFAULT_VERSION):
         self.version=version
         self.type=type
         self.flags=flags
         self.is_control=1
         self.length=0

class syn_stream_frame(controlframe):
    """
    +----------------------------------+
    |1|     version(15)  |       1     |
    +----------------------------------+
    | Flags (8)  |  Length (24 bits)   |
    +----------------------------------+
    |X|          Stream-ID (31bits)    |
    +----------------------------------+
    |X|Associated-To-Stream-ID (31bits)|
    +----------------------------------+
    | Pri | Unused    |                |
    +------------------                |
    |     Name/value header block      |
    |             ...                  |
    """
    def __init__(self,stream_id,headers,flags=FLAG_FIN,version=DEFAULT_VERSION,assoc_stream_id=0,pri=3):
        super(syn_stream_frame,self).__init__(SYN_STREAM,flags,version)
        self.stream_id=stream_id
        self.headers=headers
        self.assoc_stream_id=assoc_stream_id
        self.pri=pri
        self.definition(version)

    def definition(self,version=DEFAULT_VERSION):
        if version==2:
            self._definition=[
                                (False,1),('stream_id',31),
                                (False,1),('assoc_stream_id',31),
                                ('pri',2),(False,14),
                                ('headers',-1)
                    ]
        if version==3: #PENDING:have to accomodate Slot field
            self._definition=[
                                (False,1),('stream_id',31),
                                (False,1),('assoc_stream_id',31),
                                ('pri',2),(False,14),
                                ('headers',-1)
                    ]



class syn_reply_frame(controlframe):
    """
    +----------------------------------+
    |1|  version(15)    |        2     |
    +----------------------------------+
    | Flags (8)  |  Length (24 bits)   |
    +----------------------------------+
    |X|          Stream-ID (31bits)    |
    +----------------------------------+
    | Unused        |                  |
    +----------------                  |
    |     Name/value header block      |
    |              ...                 |
    """
    def __init__(self,stream_id,headers,flags=FLAG_NULL,version=DEFAULT_VERSION):
        super(syn_reply_frame,self).__init__(SYN_REPLY,flags,version)
        self.stream_id=stream_id
        self.headers=headers
        self.definition(version)

    def definition(self,version=DEFAULT_VERSION):
        if (version==2):
            self._definition=[
                                (False,1),('stream_id',31),
                                (False,16),
                                ('headers',-1)
                    ]
        if (version==3):
            self._definition=[
                                (False,1),('stream_id',31),
                                ('headers',-1)
                    ]



class rst_stream_frame(controlframe):
    """
    +-------------------------------+
    |1|  version(15)   |      3     |
    +-------------------------------+
    | Flags (8)  |         8        |
    +-------------------------------+
    |X|          Stream-ID (31bits) |
    +-------------------------------+
    |          Status code          | 
    +-------------------------------+
    """
    def __init__(self,stream_id,st_code,flags=FLAG_NULL,version=DEFAULT_VERSION):
        super(rst_stream_frame,self).__init__(RST_STREAM,flags,version)
        self.stream_id=stream_id
        self.status_code=st_code
        self.definition(version)

    def definition(self,version=DEFAULT_VERSION):
        if (version==2) or (version==3):
            self._definition=[
                                (False,1),('stream_id',31),
                                ('status_code',32)
                    ]


class settings_frame(controlframe):
    """
    +----------------------------------+
    |1|   version(15)    |       4     |
    +----------------------------------+
    | Flags (8)  |  Length (24 bits)   |
    +----------------------------------+
    |         Number of entries        |
    +----------------------------------+
    |          ID/Value Pairs          |
    |             ...                  |
    """

    def __init__(self,id_pairs,flags=FLAG_NULL,version=DEFAULT_VERSION):
        super(settings_frame,self).__init__(SETTINGS,flags,version)
        self.id_pairs=id_pairs
        self.no_of_pairs=len(id_pairs)
        self.definition(version)

    def definition(self,version=DEFAULT_VERSION):
        if (version==2) or (version==3):
            self._definition=[
                                ('no_of_pairs',32),
                                ('id_pairs',-1)
                    ]


class noop_frame(controlframe):
    """
    +----------------------------------+
    |1|  version(15)   |       5     |
    +----------------------------------+
    | 0 (Flags)  |    0 (Length)       |
    +----------------------------------+
    """
    def __init__(self,flags=FLAG_NULL,version=DEFAULT_VERSION):
        super(noop_frame,self).__init__(NOOP,flags,version)
        self.definition(version)

    def definition(self,version=DEFAULT_VERSION):
        if (version==2) or (version==3):
            self._definition=[]


class ping_frame(controlframe):
    """
    +----------------------------------+
    |1|   version(15)  |       6     |
    +----------------------------------+
    | 0 (flags) |     4 (length)       |
    +----------------------------------|
    |            32-bit ID             |
    +----------------------------------+
    """
    def __init__(self,ping_id,flags=FLAG_NULL,version=DEFAULT_VERSION):
        super(ping_frame,self).__init__(PING,flags,version)
        self.ping_id=ping_id
        self.definition(version)

    def definition(self,version=DEFAULT_VERSION):
        if (version==2) or (version==3):
            self._definition=[
                                ('ping_id',32),
                    ]


class goaway_frame(controlframe):
    """
    +----------------------------------+
    |1|  version(15)   |       7     |
    +----------------------------------+
    | 0 (flags) |     4 (length)       |
    +----------------------------------|
    |X|  Last-good-stream-ID (31 bits) |
    +----------------------------------+
    """
    def __init__(self,last_stream_id,flags=FLAG_NULL,version=DEFAULT_VERSION):
        super(goaway_frame,self).__init__(GOAWAY,flags,version)
        self.last_stream_id=last_stream_id
        self.definition(version)

    def definition(self,version=DEFAULT_VERSION):
        if (version==2) or (version==3):
            self._definition=[
                                ('last_stream_id',32),
                    ]


class header_frame(controlframe):
    """
    +----------------------------------+
    |C|   version(15)   |      8       |
    +----------------------------------+
    | Flags (8)  |  Length (24 bits)   |
    +----------------------------------+
    |X|          Stream-ID (31bits)    |
    +----------------------------------+
    |  Unused (16 bits) |              |
    |--------------------              |
    | Name/value header block          |
    +----------------------------------+
    """

    def __init__(self,stream_id,headers,flags=FLAG_FIN,version=DEFAULT_VERSION):
        super(header_frame,self).__init__(HEADERS,flags,version)
        self.stream_id=stream_id
        self.headers=headers
        self.definition(version)

    def definition(self,version=DEFAULT_VERSION):
        if (version==2) or (version==3):
            self._definition=[
                                (False,1),('stream_id',31),
                                (False,16),
                                ('headers',-1)
                    ]

