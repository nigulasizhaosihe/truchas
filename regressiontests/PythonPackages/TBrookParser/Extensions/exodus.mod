VH 0 0 3 0 0 0
MODULE EXODUS,1 0 0
FILE 0,../../../../build/linux.x86_64.nag.serial.dbg/exodus.f90
USE EXODUS_MESH_UTILITIES 2
USE EXODUS_TRUCHAS_HACK 2
USE EXODUS_ERRORS 2,ONLY:EXO_ERR_STR=>EXO_ERR_STR
USE EXODUS_MESH_WRITER 2
USE EXODUS_MESH_READER 2
USE EXODUS_MESH_TYPE 2
REF MAX_LINE_LENGTH(MAX_LINE_LENGTH@EXODUS_MESH_TYPE),2
REF MAX_STR_LENGTH(MAX_STR_LENGTH@EXODUS_MESH_TYPE),2
END