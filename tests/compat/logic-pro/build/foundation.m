#import <Foundation/Foundation.h>
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
                printf("P003_FOUNDATION nonce=%s items=%s count=3 answer=42 bytes=007fff missing=nil\n",
                    [nonce UTF8String], [joined UTF8String]);
            }
        }
    } @catch (NSException *exception) {
        fprintf(stderr, "P003_FOUNDATION_ERROR exception=%s\n", [[exception name] UTF8String]);
        result = 22;
    }
    [pool drain];
    return result;
}
