# Mapping table with all metadata types and all file types:

| Metadata Type | Description | File Types |
|---------------|-------------|------------|
| **PEMetadata** | Windows executables and legacy DOS formats | PE, Malformed PE, DOS |
| **ELFMetadata** | Linux/Unix executables and kernel images | ELF, Linux Kernel Image |
| **MachOMetadata** | Apple/macOS native executables and packages | MACHOFAT, MACHOFAT64, EFIFAT, MACHO32, MACHO64, IPA, MACOS_DMG |
| **CoffMetadata** | Common Object File Format family (Unix/legacy) | COFF, XCOFF32, XCOFF64, ECOFF |
| **JavaMetadata** | Java bytecode and Android packages | JAVACLASS, JAR, WAR, EAR, APK |
| **AOUTMetadata** | Legacy Unix a.out executable format | A.OUT big, A.OUT little |
| **RPMMetadata** | Red Hat Package Manager packages | RPM Package |
| **UbootImageMetadata** | U-Boot bootloader images (embedded systems) | UIMAGE |
| **DockerImageMetadata** | Docker container image formats | DOCKER_GZIP, DOCKER_TAR |
| **OleMetadata** | Microsoft OLE/COM compound documents and installers | OLE, MSCAB, ISCAB, MSIX |
| **NativeMetadata** | LLVM compiler intermediate representations | LLVM_BITCODE, LLVM_IR |
| **OtherMetadata** | Archives, compressed files, and miscellaneous formats | GZIP, BZIP2, XZ, TAR, RAR, ZIP, AR_LIB, OMF_LIB, ZLIB, CPIO_BIN big, CPIO_BIN little, CPIO_ASCII_OLD, CPIO_ASCII_NEW, CPIO_ASCII_NEW_CRC, ZSTANDARD, ZSTANDARD_DICTIONARY, ISO_9660_CD |

**Notes:**
- **JavascriptMetadata** is defined but has no file types mapped (no JS-related types in your enum)
- All 52 file type enum values are accounted for
- All 13 metadata types are included
- Each file type appears exactly once

If you want to use JavascriptMetadata, you'll need to add file types like "JS", "NODE", "JAVASCRIPT" to your enum and map them accordingly.

# Implementation
FileType is an enum near the beginning of the `observation.schema.json`.

Each specific metadata type is defined as `OneOf` like:

```JSON
      "oneOf": [
        { 
          "$ref": "#/$defs/AOUTMetadata",
          "x-duckdb-table": "aout_metadata",
          "x-duckdb-pk": "observation_uuid",
          "x-duckdb-when": ["A.OUT big", "A.OUT little"]

        },
```

Then details later in the file, via the `#/$defs` reference:

```JSON
    "AOUTMetadata": {
      "type": "object",
      "required": [ "aoutMachineType" ],
      "properties": {
        "aoutMachineType": { "type": "string" }
      }
    },
```