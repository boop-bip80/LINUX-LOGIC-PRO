#import <AppKit/AppKit.h>
#include <stdio.h>
#include <string.h>
#include "images.h"

@interface P003View : NSView {
@public
    NSString *challenge;
    NSMutableString *received;
    unsigned clicks;
    unsigned draws;
    BOOL ready;
    BOOL acknowledged;
    BOOL invalid;
}
@end

@implementation P003View
- (BOOL)acceptsFirstResponder { return YES; }
- (BOOL)acceptsFirstMouse:(NSEvent *)event { (void)event; return YES; }
- (BOOL)isOpaque { return YES; }
- (void)drawRect:(NSRect)rect {
    (void)rect;
    NSRect left = [self bounds];
    left.size.width /= 2;
    NSRect right = left;
    right.origin.x += left.size.width;
    [(ready ? [NSColor greenColor] : [NSColor redColor]) setFill];
    NSRectFill(left);
    [(ready ? [NSColor yellowColor] : [NSColor blueColor]) setFill];
    NSRectFill(right);
    ++draws;
}
- (void)mouseDown:(NSEvent *)event {
    NSPoint point = [self convertPoint:[event locationInWindow] fromView:nil];
    if (!NSPointInRect(point, [self bounds]) || ++clicks != 1) {
        invalid = YES;
        return;
    }
    [[self window] makeFirstResponder:self];
}
- (void)keyDown:(NSEvent *)event {
    NSString *characters = [event characters];
    if ([characters isEqualToString:@"\r"] || [characters isEqualToString:@"\n"]) {
        if (!ready || clicks != 1 || draws < 2) invalid = YES;
        else acknowledged = YES;
        return;
    }
    if (!characters || clicks != 1 || ready) { invalid = YES; return; }
    [received appendString:characters];
    if (![challenge hasPrefix:received]) { invalid = YES; return; }
    if ([received isEqualToString:challenge]) {
        ready = YES;
        [self setNeedsDisplay:YES];
        [[self window] setTitle:[@"P003_READY_" stringByAppendingString:challenge]];
    }
}
- (void)dealloc {
    [challenge release];
    [received release];
    [super dealloc];
}
@end

int main(int argc, char **argv) {
    if (argc != 2 || strlen(argv[1]) != 16 || strspn(argv[1], "0123456789abcdef") != 16) {
        fputs("P003_GUI_ERROR invalid challenge\n", stderr);
        return 64;
    }
    setvbuf(stdout, NULL, _IOLBF, 0);
    NSAutoreleasePool *pool = [NSAutoreleasePool new];
    int result = p003_framework_images();
    if (result) { [pool drain]; return result; }
    @try {
        NSApplication *app = [NSApplication sharedApplication];
        NSWindow *window = [[NSWindow alloc]
            initWithContentRect:NSMakeRect(160, 160, 400, 240)
            styleMask:NSTitledWindowMask backing:NSBackingStoreBuffered defer:NO];
        P003View *view = [[P003View alloc] initWithFrame:NSMakeRect(0, 0, 400, 240)];
        if (!app || !window || !view) {
            fputs("P003_GUI_ERROR object allocation\n", stderr);
            return 40;
        }
        view->challenge = [[NSString stringWithUTF8String:argv[1]] copy];
        view->received = [[NSMutableString alloc] init];
        [window setReleasedWhenClosed:NO];
        [window setContentView:view];
        [window setTitle:[@"P003_WAIT_" stringByAppendingString:view->challenge]];
        [app finishLaunching];
        [window makeKeyAndOrderFront:nil];
        [window makeFirstResponder:view];
        [window display];
        [window flushWindow];
        NSDate *deadline = [NSDate dateWithTimeIntervalSinceNow:50];
        while (!view->acknowledged && !view->invalid && [deadline timeIntervalSinceNow] > 0) {
            NSAutoreleasePool *iteration = [NSAutoreleasePool new];
            NSEvent *event = [app nextEventMatchingMask:NSAnyEventMask
                untilDate:[NSDate dateWithTimeIntervalSinceNow:0.1]
                inMode:NSDefaultRunLoopMode dequeue:YES];
            if (event) [app sendEvent:event];
            [window displayIfNeeded];
            [window flushWindowIfNeeded];
            [iteration drain];
        }
        if (view->invalid || !view->acknowledged || !view->ready ||
            view->clicks != 1 || view->draws < 2 || ![window isVisible]) {
            fprintf(stderr, "P003_GUI_ERROR roundtrip clicks=%u draws=%u ready=%d ack=%d invalid=%d\n",
                view->clicks, view->draws, view->ready, view->acknowledged, view->invalid);
            result = 41;
        } else {
            printf("P003_GUI nonce=%s clicks=1 keys=16 rendered=2 acknowledged=1\n", argv[1]);
        }
        [window orderOut:nil];
        [window close];
        [view release];
        [window release];
    } @catch (NSException *exception) {
        fprintf(stderr, "P003_GUI_ERROR exception=%s\n", [[exception name] UTF8String]);
        result = 42;
    }
    [pool drain];
    return result;
}
