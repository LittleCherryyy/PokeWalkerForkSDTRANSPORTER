/* V6.6: DSi -> Android TCP/30821: multiple OP_PING frames on ONE socket.
   No ROM/save/walker access. DSWifi close() hung in V6.4, so this test
   deliberately does not call close(). Restart DSi after running tests.
   Requires updated DirectSyncService.java; old V18 Android closes after 1 PING. */
#include "direct_ping.h"
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <netinet/in.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <stdint.h>

#define DIRECT_PORT 30821
#define HEADER_SIZE 88
#define OP_PING 4
#define OP_OK 0x80
#define VERSION 1
#define IO_SECONDS 4

static int fd_session=-1;
static int state=0; /* 0=not started, 1=connected, -1=failed (restart needed) */
static int err_socket=0;
static int requests=0;
static unsigned echo_blocks=0,echo_bytes=0;
unsigned pw_direct_echo_blocks(void){return echo_blocks;}
unsigned pw_direct_echo_bytes(void){return echo_bytes;}
int pw_direct_socket_errno(void){return err_socket;}
int pw_direct_request_count(void){return requests;}
int pw_direct_connection_alive(void){return state==1;}
static void progress(pw_direct_progress_fn cb,const char *phase,int code){
    if(cb) cb(phase,code,err_socket);
}
static uint32_t be32(const uint8_t *b){
    return ((uint32_t)b[0]<<24)|((uint32_t)b[1]<<16)|((uint32_t)b[2]<<8)|b[3];
}
static int wait_ready(int fd,int write_mode){
    fd_set f;FD_ZERO(&f);FD_SET(fd,&f);
    struct timeval tv={IO_SECONDS,0};
    return select(fd+1,write_mode?NULL:&f,write_mode?&f:NULL,NULL,&tv);
}
static int io_exact(int fd,uint8_t *buf,unsigned total,int send_mode,pw_direct_progress_fn cb){
    unsigned pos=0;
    while(pos<total){
        progress(cb,send_mode?"esperando envio":"esperando resposta",0);
        int ready=wait_ready(fd,send_mode);
        if(ready<=0){err_socket=ready==0?ETIMEDOUT:errno;return send_mode?-8:-9;}
        progress(cb,send_mode?"send()":"recv()",0);
        int n=send_mode?send(fd,buf+pos,total-pos,0):recv(fd,buf+pos,total-pos,0);
        if(n<=0){err_socket=n==0?ECONNRESET:errno;return send_mode?-8:-9;}
        pos+=(unsigned)n;
    }
    return 0;
}
/* Same TCP setup as the hardware-verified V6.6 PING path. */
static int ensure_session(uint32_t gateway,pw_direct_progress_fn cb){
    struct sockaddr_in sa;
    int rc;
    err_socket=0;
    if(state==-1){progress(cb,"sessao encerrada: reinicie",-20);return -20;}
    if(!gateway){progress(cb,"gateway ausente",-1);return -1;}
    if(state==1)return 0;
    progress(cb,"socket(): sessao nova",0);
    fd_session=socket(AF_INET,SOCK_STREAM,0);
    if(fd_session<0){err_socket=errno;state=-1;progress(cb,"socket() falhou",-2);return -2;}
    memset(&sa,0,sizeof(sa));sa.sin_family=AF_INET;
    sa.sin_addr.s_addr=gateway;sa.sin_port=htons(DIRECT_PORT);
    progress(cb,"connect() bloqueante",0);
    rc=connect(fd_session,(struct sockaddr*)&sa,sizeof(sa));
    if(rc<0){err_socket=errno;state=-1;progress(cb,"connect() falhou",-4);return -4;}
    state=1;
    progress(cb,"sessao TCP conectada",0);
    return 0;
}
int pw_direct_ping_persistent(uint32_t gateway,pw_direct_progress_fn cb){
    int rc;
    uint8_t frame[HEADER_SIZE];
    rc=ensure_session(gateway,cb);
    if(rc)return rc;
    memset(frame,0,sizeof(frame));
    memcpy(frame,"PWDSI001",8);
    frame[8]=VERSION;frame[9]=OP_PING;
    rc=io_exact(fd_session,frame,HEADER_SIZE,1,cb);
    if(rc!=0)goto bad;
    memset(frame,0,sizeof(frame));
    rc=io_exact(fd_session,frame,HEADER_SIZE,0,cb);
    if(rc!=0)goto bad;
    progress(cb,"validar header OP_OK",0);
    if(memcmp(frame,"PWDSI001",8)||frame[8]!=VERSION){rc=-10;goto bad;}
    if(frame[9]!=OP_OK){rc=-11;goto bad;}
    if(be32(frame+12)!=0){rc=-12;goto bad;}
    if(be32(frame+16)!=0){rc=-13;goto bad;}
    requests++;
    progress(cb,"OP_OK: socket reutilizavel",0);
    return 0;
bad:
    state=-1; /* Nao fazer close(): pode travar na build DSWifi testada. */
    progress(cb,"sessao falhou: reinicie",rc);
    return rc;
}

/* V6.7 TEST ONLY. Each 512-byte block contains a four-byte big-endian
   block index followed by 508 deterministic synthetic bytes. Nothing is
   read from game, EEPROM, or save. No close() in this hardware test. */
#define OP_TEST_ECHO 5
#define TEST_BLOCK 512u
static void put_be32(uint8_t *b,uint32_t v){
    b[0]=(uint8_t)(v>>24);b[1]=(uint8_t)(v>>16);
    b[2]=(uint8_t)(v>>8);b[3]=(uint8_t)v;
}
static uint32_t crc32_test(const uint8_t *p,unsigned n){
    uint32_t c=0xffffffffu;
    for(unsigned i=0;i<n;i++){
        c^=p[i];
        for(int j=0;j<8;j++)c=(c>>1)^(0xedb88320u & (0u-(c&1u)));
    }
    return c^0xffffffffu;
}
int pw_direct_echo_persistent(uint32_t gateway,unsigned total,pw_direct_progress_fn cb){
    if(total!=2048u && total!=8192u){progress(cb,"tamanho de teste invalido",-30);return -30;}
    int rc=ensure_session(gateway,cb);
    if(rc)return rc;
    uint8_t header[HEADER_SIZE];
    static uint8_t expected[TEST_BLOCK];
    static uint8_t response[TEST_BLOCK];
    for(unsigned block=0;block<total/TEST_BLOCK;block++){
        put_be32(expected,block);
        for(unsigned j=4;j<TEST_BLOCK;j++){
            unsigned global=(block*508u)+(j-4u);
            expected[j]=(uint8_t)((global*73u+19u)&255u);
        }
        memset(header,0,sizeof(header));
        memcpy(header,"PWDSI001",8);
        header[8]=VERSION;header[9]=OP_TEST_ECHO;
        put_be32(header+12,TEST_BLOCK);
        put_be32(header+16,crc32_test(expected,TEST_BLOCK));
        progress(cb,"eco: enviar cabecalho",0);
        rc=io_exact(fd_session,header,HEADER_SIZE,1,cb);if(rc)goto failed;
        progress(cb,"eco: enviar bloco",0);
        rc=io_exact(fd_session,expected,TEST_BLOCK,1,cb);if(rc)goto failed;
        progress(cb,"eco: receber cabecalho",0);
        rc=io_exact(fd_session,header,HEADER_SIZE,0,cb);if(rc)goto failed;
        if(memcmp(header,"PWDSI001",8)!=0||header[8]!=VERSION||header[9]!=OP_OK){rc=-31;goto failed;}
        if(be32(header+12)!=TEST_BLOCK || be32(header+16)!=crc32_test(expected,TEST_BLOCK)){
            rc=-32;goto failed;
        }
        progress(cb,"eco: receber bloco",0);
        rc=io_exact(fd_session,response,TEST_BLOCK,0,cb);if(rc)goto failed;
        if(memcmp(expected,response,TEST_BLOCK)!=0||crc32_test(response,TEST_BLOCK)!=be32(header+16)){
            rc=-33;goto failed;
        }
        echo_blocks++;
        echo_bytes+=TEST_BLOCK;
        progress(cb,"eco: bloco CRC OK",0);
    }
    progress(cb,"eco: transferencia OK",0);
    return 0;
failed:
    state=-1; /* close() was observed to hang in V6.4; reboot DSi. */
    progress(cb,"eco falhou: reinicie",rc);
    return rc;
}
