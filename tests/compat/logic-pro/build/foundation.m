#import <Foundation/Foundation.h>
#import <xpc/xpc.h>
#include <vproc_priv.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc != 2 || strlen(argv[1]) == 0 || strlen(argv[1]) > 64) {
        fputs("P003_FOUNDATION_ERROR invalid arguments\n", stderr);
        return 64;
    }
    NSAutoreleasePool *pool = [NSAutoreleasePool new];
    int result = 0;
    @try {
        NSMutableArray *array = [NSMutableArray arrayWithObjects:@"gamma", @"alpha", @"beta", nil];
        [array sortUsingSelector:@selector(compare:)];
        NSString *joined = [array componentsJoinedByString:@"|"];
        NSMutableDictionary *dict = [NSMutableDictionary dictionary];
        [dict setObject:array forKey:@"items"];
        [dict setObject:[NSNumber numberWithInt:42] forKey:@"answer"];
        const unsigned char bytes[] = {0, 127, 255};
        NSData *data = [NSData dataWithBytes:bytes length:sizeof(bytes)];
        if (!pool || !array || !dict || !data ||
            ![joined isEqualToString:@"alpha|beta|gamma"] ||
            [[dict objectForKey:@"items"] count] != 3 ||
            [[dict objectForKey:@"answer"] intValue] != 42 ||
            [dict objectForKey:@"missing"] != nil ||
            [data length] != sizeof(bytes) ||
            memcmp([data bytes], bytes, sizeof(bytes)) != 0) {
            fputs("P003_FOUNDATION_ERROR object assertion\n", stderr);
            result = 20;
        } else {
            NSString *nonce = [NSString stringWithUTF8String:argv[1]];
            if (!nonce || strcmp([nonce UTF8String], argv[1]) != 0) {
                result = 21;
            } else {
                // Verify the actual installed libxpc API shares the live
                // liblaunch lifecycle state. A silent stub cannot satisfy
                // these four independently observed counter transitions.
                size_t baseline = _vproc_transaction_count();
                xpc_transaction_begin();
                size_t first = _vproc_transaction_count();
                _vproc_transaction_begin();
                size_t nested = _vproc_transaction_count();
                xpc_transaction_end();
                size_t partly_done = _vproc_transaction_count();
                _vproc_transaction_end();
                size_t restored = _vproc_transaction_count();
                if (baseline >= (size_t)-2 || first != baseline + 1 ||
                    nested != baseline + 2 || partly_done != baseline + 1 ||
                    restored != baseline) {
                    fprintf(stderr, "P003_FOUNDATION_ERROR transaction interop counts=%zu|%zu|%zu|%zu|%zu\n",
                        baseline, first, nested, partly_done, restored);
                    result = 23;
                } else {
                    printf("P003_FOUNDATION nonce=%s items=%s count=3 answer=42 bytes=007fff missing=nil\n",
                        [nonce UTF8String], [joined UTF8String]);
                    printf("P003_TRANSACTION nonce=%s deltas=1|2|1|0\n", [nonce UTF8String]);
                }
            }
        }
    } @catch (NSException *exception) {
        fprintf(stderr, "P003_FOUNDATION_ERROR exception=%s\n", [[exception name] UTF8String]);
        result = 22;
    }
    [pool drain];
    return result;
}
