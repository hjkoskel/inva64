;
; Vector-quantised digi player (from invasoundboard/src/play.s).
;
; Each data byte is the number of a codeword; a codeword is VQ_LEN 4-bit
; samples, stored as VQ_LEN tables of 256 bytes (_codebook + j*256).
; Samples are written to the SID volume register. Timing comes from CIA2
; timer A, which is polled.
;
; Silence escape: the codeword VQ_ESC is followed by a count byte n and is
; played n times. Its samples are all the mid level, so this is n vectors
; of silence in two bytes.
;
; Clip data can be anywhere in RAM, also under the I/O area ($D000-$DFFF):
; each index byte is read with $01=$34 (all RAM), and the SID and the CIA
; are used with $01=$35 (I/O on).
;
; C interface:
;   digi_begin();            interrupts off, SID set up for samples
;   digi_play(clip);         play one clip (may be called several times)
;   digi_end();              SID back to the music, interrupts on
;
; The music stops while a clip plays, because interrupts are off.
;
        .include "vq.inc"               ; VQ_LEN, LATCH_PAL, VQ_ESC (generated)

        .export _digi_begin, _digi_play, _digi_end
        .import _codebook, _sample_addr, _sample_len
        .importzp ptr1, ptr2, tmp1

SID_VOL  = $D418
CIA2_TA  = $DD04
CIA2_ICR = $DD0D
CIA2_CRA = $DD0E

.segment "CODE"

; Three voices hold a constant level (test bit + pulse, gate on, sustain
; max), so that $D418 writes are audible on the 8580 as well.
_digi_begin:
        sei
        ldx     #14
@v:     lda     #$08                    ; gate off first: the music may have
        sta     $D404,x                 ; left it on, and the envelope only
        lda     #$00                    ; rises to full level on a new gate
        sta     $D405,x                 ; attack/decay
        lda     #$F0
        sta     $D406,x                 ; sustain=15, release=0
        lda     #$49
        sta     $D404,x                 ; test + pulse + gate
        txa
        sec
        sbc     #7
        tax
        bpl     @v
        lda     #8                      ; mid level = silence
        sta     SID_VOL
        rts

; Voices off. The music player sets the volume again at its next call and
; the voices at their next notes.
_digi_end:
        ldx     #14
@v:     lda     #$00
        sta     $D404,x
        sta     $D406,x
        txa
        sec
        sbc     #7
        tax
        bpl     @v
        cli
        rts

; void __fastcall__ digi_play(unsigned char clip)
_digi_play:
        asl     a
        tax
        lda     _sample_addr,x
        sta     ptr1
        lda     _sample_addr+1,x
        sta     ptr1+1
        lda     _sample_len,x
        sta     ptr2
        lda     _sample_len+1,x
        sta     ptr2+1

        lda     $01
        pha
        lda     #$35                    ; all RAM + I/O
        sta     $01

        lda     #$7F
        sta     CIA2_ICR                ; no CIA2 NMIs
        lda     #<LATCH_PAL
        sta     CIA2_TA
        lda     #>LATCH_PAL
        sta     CIA2_TA+1
        lda     #$11                    ; start, continuous, force load
        sta     CIA2_CRA
        lda     CIA2_ICR                ; acknowledge pending flags

@loop:  jsr     fetch                   ; codeword number
        tax
        ldy     #1
        sty     tmp1                    ; play it once ...
        cpx     #VQ_ESC
        bne     @play
        jsr     advance                 ; ... or as often as the next byte says
        jsr     fetch
        sta     tmp1
@play:  lda     #1                      ; timer A underflow bit (BIT keeps A)
.repeat VQ_LEN, I
        ldy     _codebook + I*256,x
:       bit     CIA2_ICR
        beq     :-
        sty     SID_VOL
.endrepeat
        dec     tmp1
        bne     @play

        jsr     advance
        bne     @loop

        lda     #8                      ; back to silence level
        sta     SID_VOL
        lda     #$00
        sta     CIA2_CRA                ; stop timer
        pla
        sta     $01
        rts

; Read the data byte at ptr1 with all RAM visible: the clip may be under
; the I/O area. Keeps X.
fetch:  ldy     #$34
        sty     $01
        ldy     #0
        lda     (ptr1),y
        ldy     #$35
        sty     $01
        rts

; Step to the next data byte. Returns Z set when the clip has ended.
advance:
        inc     ptr1
        bne     @cnt
        inc     ptr1+1
@cnt:   lda     ptr2                    ; 16-bit byte counter
        bne     @dec
        dec     ptr2+1
@dec:   dec     ptr2
        lda     ptr2
        ora     ptr2+1
        rts
