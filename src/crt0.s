;
; Start-up code of the main game file.
;
; The boot file loads the main file to $0400 and jumps to $0800, which is
; the first byte of the STARTUP segment. The title picture is on screen at
; that point, so nothing here touches the VIC.
;
        .export   __STARTUP__ : absolute = 1
        .import   _main, zerobss
        .import   __MAIN_START__, __MAIN_SIZE__, __STACKSIZE__
        .importzp sp

.segment "LOADADDR"
        .word   $0400

.segment "STARTUP"
        sei
        cld
        ldx     #$FF
        txs
        lda     #$36                    ; BASIC ROM out, KERNAL and I/O in
        sta     $01
        jsr     zerobss
        lda     #<(__MAIN_START__ + __MAIN_SIZE__ + __STACKSIZE__)
        sta     sp
        lda     #>(__MAIN_START__ + __MAIN_SIZE__ + __STACKSIZE__)
        sta     sp+1
        jsr     _main
@stop:  jmp     @stop
