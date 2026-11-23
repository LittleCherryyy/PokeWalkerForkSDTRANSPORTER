/* JVM interoperability: emit exact C client request, then validate a response
 * created by the real Android DirectSyncProtocol.java. No socket or save.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "walker_ping_engine.h"

typedef struct { const uint8_t *reply; unsigned at, sent; } Interop;
static int mockSend(void *x,uint8_t *bytes,unsigned n){
    Interop *io=x;
    if(n==0)return -1;
    (void)bytes;io->sent+=n;return (int)n;
}
static int mockRecv(void *x,uint8_t *bytes,unsigned n){
    Interop *io=x;
    if(io->at+n>WALKER_DIRECT_HEADER_SIZE)return -1;
    memcpy(bytes,io->reply+io->at,n);io->at+=n;return (int)n;
}
int main(int argc,char **argv) {
    if(argc!=3){fputs("Usage: ping_interop request|response FILE\n",stderr);return 2;}
    WalkerPing ping;
    walkerPingStart(&ping,0,60);
    if(ping.state!=WALKER_PING_SENDING)return 3;
    if(!strcmp(argv[1],"request")) {
        FILE *out=fopen(argv[2],"wb");
        if(!out)return 4;
        int ok=fwrite(ping.tx,1,WALKER_DIRECT_HEADER_SIZE,out)==WALKER_DIRECT_HEADER_SIZE;
        fclose(out);return ok?0:5;
    }
    if(strcmp(argv[1],"response"))return 2;
    uint8_t reply[WALKER_DIRECT_HEADER_SIZE];
    FILE *in=fopen(argv[2],"rb");
    if(!in)return 6;
    int ok=fread(reply,1,sizeof(reply),in)==sizeof(reply) && fgetc(in)==EOF;
    fclose(in);if(!ok)return 7;
    Interop state={reply,0,0};
    WalkerPingIo io={&state,mockSend,mockRecv};
    if(walkerPingStep(&ping,&io,0)!=WALKER_PING_RECEIVING)return 8;
    if(walkerPingStep(&ping,&io,1)!=WALKER_PING_OK)return 9;
    if(state.sent!=88u || state.at!=88u || ping.error!=0)return 10;
    puts("PASS V7.2 interoperability: Android Java OP_OK accepted by C parser");
    return 0;
}
