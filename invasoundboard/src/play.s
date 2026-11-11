;
; Vector-quantised digi player.
;
; Each data byte is the number of a codeword; a codeword is VQ_LEN 4-bit
; samples, stored as VQ_LEN tables of 256 bytes (_codebook + j*256).
; Samples are written to the SID volume register.
;
; Playback runs with interrupts disabled and BASIC+KERNAL ROM banked out
; ($01=$35) so that sample data can also live in the RAM under the KERNAL
; ($E000-$FFF9). Sample timing comes from CIA2 timer A, which is polled
; (its NMI stays disabled), so VIC bad lines only add a few cycles jitter.
;
; C interface (set the variables, then call play()):
;   play_ptr   - address of the codeword indices
;   play_len   - number of index bytes (must be > 0)
;   play_latch - CIA timer latch = CPU clock / sample rate - 1
;

        .include "vq.inc"               ; VQ_LEN (generated)

        .export _play, _play_init
        .export _play_ptr, _play_len, _play_latch
        .import _codebook
        .importzp ptr1, ptr2

SID_VOL  = $D418
CIA2_TA  = $DD04
CIA2_ICR = $DD0D
CIA2_CRA = $DD0E

.segment "BSS"
_play_ptr:   .res 2
_play_len:   .res 2
_play_latch: .res 2

.segment "CODE"

; Init SID so that $D418 writes are audible on the 8580 as well:
; three voices hold a constant DC level (test bit + pulse, gate on,
; sustain max). Also point the RAM NMI vector at an RTI, since the
; KERNAL is banked out while playing.
_play_init:
        ldx #14
@v:     lda #$00
        sta $D405,x             ; attack/decay
        lda #$F0
        sta $D406,x             ; sustain=15, release=0
        lda #$49
        sta $D404,x             ; test + pulse + gate
        txa
        sec
        sbc #7
        tax
        bpl @v
        lda #8                  ; mid level = silence
        sta SID_VOL
        lda #<nmi_rti
        sta $FFFA
        lda #>nmi_rti
        sta $FFFB
        rts

_play:
        php
        sei
        lda $01
        pha
        lda #$35                ; RAM at $A000-$BFFF/$E000-$FFFF, I/O on
        sta $01

        lda _play_ptr
        sta ptr1
        lda _play_ptr+1
        sta ptr1+1
        lda _play_len
        sta ptr2
        lda _play_len+1
        sta ptr2+1

        lda #$7F
        sta CIA2_ICR            ; no CIA2 NMIs
        lda _play_latch
        sta CIA2_TA
        lda _play_latch+1
        sta CIA2_TA+1
        lda #$11                ; start, continuous, force load
        sta CIA2_CRA
        lda CIA2_ICR            ; acknowledge pending flags

@loop:  ldy #0
        lda (ptr1),y            ; codeword number
        tax
        lda #1                  ; timer A underflow bit (BIT keeps A)
.repeat VQ_LEN, I
        ldy _codebook + I*256,x
:       bit CIA2_ICR
        beq :-
        sty SID_VOL
.endrepeat

        inc ptr1
        bne @cnt
        inc ptr1+1
@cnt:   lda ptr2                ; 16-bit byte counter
        bne @dec
        dec ptr2+1
@dec:   dec ptr2
        lda ptr2
        ora ptr2+1
        bne @loop

        lda #8                  ; back to silence level
        sta SID_VOL
        lda #$00
        sta CIA2_CRA            ; stop timer
        pla
        sta $01
        plp
        rts

nmi_rti:
        rti
