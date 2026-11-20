/* Project RETR0: place all patch code and its constant data in the code cave of libRealRacing3.so (arm64,
   RR3 14.0.1): 0x938 bytes of zero padding at 0x9876c8, inside the executable segment. store_grant_patch.S must
   be the first input so that grant_entry lands exactly at the cave start. */
ENTRY(grant_entry)
SECTIONS
{
    . = 0x9876c8;
    .text : {
        *(.text .text.*)
        *(.rodata .rodata.*)
    }
    /DISCARD/ : {
        *(.comment) *(.note .note.*) *(.eh_frame .eh_frame_hdr) *(.data .data.* .bss .bss.*)
    }
}
