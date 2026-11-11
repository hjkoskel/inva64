;
; Boot file: shows the title picture and loads the main game file.
;
; It also carries the sample clips that live in the RAM under the I/O area
; ($D000-$DFFF), because the KERNAL LOAD cannot write there.
;
;   1. copy the title bitmap to $E000 and the clips to $D000 (all RAM on)
;   2. copy the title screen data to $CC00 and the colours to $D800
;   3. show the picture (VIC bank 3, multicolor bitmap)
;   4. copy the loader stub to $0334 and run it: it loads "MAIN" to $0400
;      and jumps to $0800
;
        .include "title.inc"            ; TITLE_BG (generated)

MAIN_ENTRY = $0800
STUB_ADDR  = $0334

SRC = $FB
DST = $FD

.macro  copy    from, to, count
        lda     #<(from)
        sta     SRC
        lda     #>(from)
        sta     SRC+1
        lda     #<(to)
        sta     DST
        lda     #>(to)
        sta     DST+1
        lda     #<(count)
        sta     len
        lda     #>(count)
        sta     len+1
        jsr     copymem
.endmacro

.segment "CODE"
        .word   $0801                   ; load address
        .word   @next, 10               ; 10 SYS2061
        .byte   $9E, "2061", 0
@next:  .word   0

start:  sei
        lda     #$34                    ; all RAM
        sta     $01
        copy    bitmap, $E000, 8000
        copy    hiram, $D000, hiram_end - hiram
        lda     #$37
        sta     $01
        copy    screen, $CC00, 1000
        copy    colour, $D800, 1000

        lda     #0
        sta     $D020
        sta     $D015                   ; sprites off
        lda     #TITLE_BG
        sta     $D021
        lda     $DD02
        ora     #$03
        sta     $DD02
        lda     $DD00
        and     #$FC                    ; VIC bank 3: $C000-$FFFF
        sta     $DD00
        lda     #$38                    ; screen $CC00, bitmap $E000
        sta     $D018
        lda     #$18                    ; multicolor
        sta     $D016
        lda     #$3B                    ; bitmap mode, screen on
        sta     $D011

        ldx     #stub_end - stub - 1
@cp:    lda     stub,x
        sta     STUB_ADDR,x
        dex
        bpl     @cp
        cli
        jmp     STUB_ADDR

copymem:
        ldy     #0
@loop:  lda     (SRC),y
        sta     (DST),y
        iny
        bne     @cnt
        inc     SRC+1
        inc     DST+1
@cnt:   lda     len
        bne     @dec
        dec     len+1
@dec:   dec     len
        lda     len
        ora     len+1
        bne     @loop
        rts

len:    .word   0

; Runs at $0334, outside the memory that the main file loads over.
stub:
        .org    STUB_ADDR
        lda     #0
        sta     $9D                     ; no KERNAL messages
        lda     #name_end - name
        ldx     #<name
        ldy     #>name
        jsr     $FFBD                   ; SETNAM
        ldx     $BA                     ; the drive this file came from
        bne     @dev
        ldx     #8
@dev:   lda     #1
        ldy     #1                      ; load to the address in the file
        jsr     $FFBA                   ; SETLFS
        lda     #0
        jsr     $FFD5                   ; LOAD
        bcs     @error
        jmp     MAIN_ENTRY
@error: lda     #2                      ; red border: load failed
        sta     $D020
        bne     @error
name:   .byte   "MAIN"
name_end:
        .reloc
stub_end:
        .assert stub_end - stub <= 200, error, "loader stub too long"

bitmap: .incbin "build/title_bmp.bin"
screen: .incbin "build/title_scr.bin"
colour: .incbin "build/title_col.bin"
hiram:  .incbin "build/hi.bin"
hiram_end:
        .assert hiram_end - hiram > 0, error, "build/hi.bin is empty"
