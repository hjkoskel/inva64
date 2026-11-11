;
; Frame interrupt: counts frames and plays the music.
;
; A raster interrupt fires once per frame through the KERNAL vector $0314.
; The handler calls the GoatTracker play routine ($1003) unless
; music_paused is set, as harmonia_small_run.prg does (50 times per second
; on PAL).
;
; The same interrupt also works while the KERNAL ROM is banked out ($01 =
; $35): the RAM vector at $FFFE points to a handler that saves the
; registers itself. The map unpacker uses this to keep the music playing.
;
        .export _irq_init, _wait_frame
        .export _frame, _music_paused

MUSIC_INIT  = $1000
MUSIC_PLAY  = $1003
RASTER_LINE = 251

.segment "BSS"
_frame:        .res 1                   ; +1 every frame
_music_paused: .res 1                   ; non-zero: do not call the player

.segment "CODE"

; void irq_init(void) - start the music and the frame interrupt
_irq_init:
        sei
        lda     #$7F
        sta     $DC0D                   ; CIA interrupts off
        sta     $DD0D
        lda     $DC0D                   ; acknowledge pending ones
        lda     $DD0D

        lda     #<nmi                   ; RESTORE key does nothing, with the
        sta     $0318                   ; KERNAL in ...
        sta     $FFFA                   ; ... and with it banked out
        lda     #>nmi
        sta     $0319
        sta     $FFFB

        lda     #<irq_ram               ; interrupt vector for KERNAL out
        sta     $FFFE
        lda     #>irq_ram
        sta     $FFFF

        lda     #0
        jsr     MUSIC_INIT

        lda     #RASTER_LINE
        sta     $D012
        lda     $D011
        and     #$7F
        sta     $D011
        lda     #<irq
        sta     $0314
        lda     #>irq
        sta     $0315
        lda     #$01
        sta     $D01A                   ; raster interrupt on
        sta     $D019
        cli
        rts

; Entered from the KERNAL, which has saved the registers.
irq:    jsr     tick
        jmp     $EA81                   ; KERNAL: restore registers, RTI

; Entered directly, when the KERNAL ROM is banked out.
irq_ram:
        pha
        txa
        pha
        tya
        pha
        jsr     tick
        pla
        tay
        pla
        tax
        pla
        rti

tick:   lda     #$01
        sta     $D019                   ; acknowledge
        inc     _frame
        lda     _music_paused
        bne     @skip
        jmp     MUSIC_PLAY
@skip:  rts

nmi:    rti

; void wait_frame(void) - return at the next frame interrupt
_wait_frame:
        lda     _frame
@wait:  cmp     _frame
        beq     @wait
        rts
