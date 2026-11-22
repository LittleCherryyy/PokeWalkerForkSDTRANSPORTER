/* V5: DSi -> phone hotspot gateway; RAM-only synthetic payload. */
#include "uplink.h"
#include "protocol.h"
#include <sys/socket.h>
#include <sys/select.h>
#include <netinet/in.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>

#define PW_UPLINK_PORT 30822
#define PW_MAX_TRANSFER 8192u
#define PW_BLOCK 512u
static uint8_t synthetic[PW_MAX_TRANSFER];
static uint8_t rxbuf[PW_MAX_PAYLOAD];
static unsigned session_counter=0;
static int waitfd(int fd,int forwrite){fd_set rf,wf;FD_ZERO(&rf);FD_ZERO(&wf);if(forwrite)FD_SET(fd,&wf);else FD_SET(fd,&rf);struct timeval tv={4,0};return select(fd+1,&rf,&wf,NULL,&tv)>0?0:-1;}
static int write_all(int fd,const uint8_t *p,unsigned count){unsigned at=0;while(at<count){if(waitfd(fd,1))return -1;int n=send(fd,p+at,count-at,0);if(n<=0)return -1;at+=(unsigned)n;}return 0;}
static int read_all(int fd,uint8_t *p,unsigned count){unsigned at=0;while(at<count){if(waitfd(fd,0))return -1;int n=recv(fd,p+at,count-at,0);if(n<=0)return -1;at+=(unsigned)n;}return 0;}
static int dial(uint32_t ip){
    int fd=socket(AF_INET,SOCK_STREAM,0);if(fd<0)return -1;
    struct sockaddr_in sa;memset(&sa,0,sizeof(sa));sa.sin_family=AF_INET;sa.sin_addr.s_addr=ip;sa.sin_port=htons(PW_UPLINK_PORT);
    /* A 3s pre-connect select cannot time out a blocking connect on all dswifi versions;
       real connection path is locally reachable through the hotspot. */
    if(connect(fd,(struct sockaddr*)&sa,sizeof(sa))<0){close(fd);return -1;}return fd;
}
/* Every request opens one TCP connection, matching the existing V3 design. */
static int command(uint32_t server,int action,const uint8_t *data,unsigned len,int expected,uint8_t *reply,unsigned *reply_len){
    if(len>PW_MAX_PAYLOAD)return -11;
    int fd=dial(server);if(fd<0)return -12;
    uint8_t head[PW_HEADER_SIZE];pw_write_header(head,action,data,len);
    if(write_all(fd,head,PW_HEADER_SIZE) || (len&&write_all(fd,data,len))){close(fd);return -13;}
    int ret=-14;
    if(!read_all(fd,head,PW_HEADER_SIZE)){
        unsigned a=0,n=0,crc=0;
        if(pw_parse_header(head,&a,&n,&crc)==0&&n<=PW_MAX_PAYLOAD&&(!n||!read_all(fd,rxbuf,n))){
            if(pw_crc32(rxbuf,n)==crc){
                if(a==PW_ACT_ERROR)ret=-20;
                else if((int)a==expected){if(n>16){ret=-18;}else{if(reply&&n)memcpy(reply,rxbuf,n);*reply_len=n;ret=0;}}
                else ret=-15;
            }else ret=-16;
        }
    }
    close(fd);return ret;
}
int pw_uplink_ping(uint32_t ip){
    static const uint8_t sample[]="V5-DSI-PING";uint8_t response[32];unsigned n=0;
    int e=command(ip,PW_ACT_PING,sample,sizeof(sample)-1,PW_ACT_PONG,response,&n);
    if(e)return e;
    return n==sizeof(sample)-1 && memcmp(response,sample,n)==0?0:-17;
}
int pw_uplink_transfer(uint32_t ip,unsigned total){
    if(total==0||total>PW_MAX_TRANSFER)return -21;
    for(unsigned i=0;i<total;i++)synthetic[i]=(uint8_t)((i*73u+19u)&255u);
    uint32_t crc=pw_crc32(synthetic,total);
    uint32_t id=(uint32_t)(0xA5000000u|((++session_counter)&0x00ffffffu));
    uint8_t p[8+PW_BLOCK],response[16];unsigned rlen=0;
    pw_write_be32(p,id);pw_write_be32(p+4,total);pw_write_be32(p+8,crc);
    int e=command(ip,0x10,p,12,0x90,response,&rlen);
    if(e)return e;
    if(rlen!=12||pw_read_be32(response)!=id||pw_read_be32(response+4)!=total||pw_read_be32(response+8)!=512)return -22;
    for(unsigned offset=0;offset<total;){
        unsigned chunk=total-offset;if(chunk>PW_BLOCK)chunk=PW_BLOCK;
        pw_write_be32(p,id);pw_write_be32(p+4,offset);memcpy(p+8,synthetic+offset,chunk);
        e=command(ip,0x11,p,8+chunk,0x91,response,&rlen);
        if(e)return e;
        if(rlen!=8||pw_read_be32(response)!=id||pw_read_be32(response+4)!=offset+chunk)return -23;
        offset+=chunk;
    }
    pw_write_be32(p,id);
    e=command(ip,0x12,p,4,0x92,response,&rlen);
    if(e)return e;
    return rlen==12&&pw_read_be32(response)==id&&pw_read_be32(response+4)==total&&pw_read_be32(response+8)==crc?0:-24;
}
