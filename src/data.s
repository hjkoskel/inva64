;
; Binary data made by the tools: music, packed map, cursor sprites.
;
        .export _map_bmp_z, _map_scr_z, _cursor_data

.segment "MUSIC"                        ; $1000: init, $1003: play
        .incbin "build/music.bin"

.segment "SAMPLES"
_map_bmp_z:   .incbin "build/map_bmp.z"
_cursor_data: .incbin "build/cursor.bin"

.segment "ONESHOT"                      ; used once, by playfield_show()
_map_scr_z:   .incbin "build/map_scr.z"
