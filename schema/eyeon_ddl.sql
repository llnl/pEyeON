CREATE SEQUENCE certificate_seq
;

CREATE TABLE observations (
  uuid VARCHAR PRIMARY KEY,
  bytecount BIGINT,
  compiler VARCHAR DEFAULT NULL,
  filename VARCHAR,
  filetype VARCHAR,
  imphash VARCHAR DEFAULT NULL,
  telfhash VARCHAR DEFAULT NULL,
  magic VARCHAR,
  md5 VARCHAR,
  modtime VARCHAR DEFAULT NULL,
  observation_ts VARCHAR,
  parent VARCHAR DEFAULT NULL,
  permissions VARCHAR DEFAULT NULL,
  sha1 VARCHAR,
  sha256 VARCHAR,
  ssdeep VARCHAR DEFAULT NULL,
  target_os VARCHAR DEFAULT NULL,
  authentihash VARCHAR DEFAULT NULL,
  authenticode_integrity VARCHAR DEFAULT NULL,
  algorithm VARCHAR,
  expected VARCHAR,
  actual VARCHAR,
  verified BOOLEAN
);

CREATE TABLE base_metadata (
  observation_uuid VARCHAR PRIMARY KEY,
  filetype VARCHAR,
  aoutMachineType VARCHAR DEFAULT NULL,
  coffMachineType VARCHAR DEFAULT NULL,
  dockerSPDX JSON DEFAULT NULL,
  OS VARCHAR DEFAULT NULL,
  EI_CLASS INTEGER DEFAULT NULL,
  EI_DATA INTEGER DEFAULT NULL,
  EI_VERSION INTEGER DEFAULT NULL,
  EI_OSABI INTEGER DEFAULT NULL,
  EI_ABIVERSION INTEGER DEFAULT NULL,
  E_MACHINE INTEGER DEFAULT NULL,
  elfDependencies VARCHAR[] DEFAULT NULL,
  elfRpath VARCHAR[] DEFAULT NULL,
  elfRunpath VARCHAR[] DEFAULT NULL,
  elfSoname VARCHAR[] DEFAULT NULL,
  elfInterpreter VARCHAR[] DEFAULT NULL,
  elfDynamicFlags VARCHAR[] DEFAULT NULL,
  elfDynamicFlags1 VARCHAR[] DEFAULT NULL,
  elfGnuRelro BOOLEAN DEFAULT NULL,
  elfComment VARCHAR[] DEFAULT NULL,
  elfNote VARCHAR[] DEFAULT NULL,
  elfOsAbi VARCHAR DEFAULT NULL,
  elfHumanArch VARCHAR DEFAULT NULL,
  elfArchNumber INTEGER DEFAULT NULL,
  elfArchitecture VARCHAR DEFAULT NULL,
  elfIsExe BOOLEAN DEFAULT NULL,
  elfIsLib BOOLEAN DEFAULT NULL,
  elfIsRel BOOLEAN DEFAULT NULL,
  elfIsCore BOOLEAN DEFAULT NULL,
  jsLibraries VARCHAR[] DEFAULT NULL,
  numBinaries INTEGER DEFAULT NULL,
  binaries JSON DEFAULT NULL,
  nativeLibraries JSON DEFAULT NULL,
  ole JSON DEFAULT NULL,
  peMachine VARCHAR DEFAULT NULL,
  peOperatingSystemVersion VARCHAR DEFAULT NULL,
  peSubsystemVersion VARCHAR DEFAULT NULL,
  peSubsystem VARCHAR DEFAULT NULL,
  peLinkerVersion VARCHAR DEFAULT NULL,
  peImport VARCHAR[] DEFAULT NULL,
  peIsExe BOOLEAN DEFAULT NULL,
  peIsDll BOOLEAN DEFAULT NULL,
  peIsClr BOOLEAN DEFAULT NULL,
  FileInfo JSON DEFAULT NULL,
  dllRedirectionLocal BOOLEAN DEFAULT NULL,
  rpm JSON DEFAULT NULL,
  uimage_header JSON DEFAULT NULL,
  description VARCHAR DEFAULT NULL,
  FOREIGN KEY (observation_uuid) REFERENCES observations(uuid)
);

CREATE TABLE signatures (
  signature_id VARCHAR PRIMARY KEY,
  observation_uuid VARCHAR,
  signers VARCHAR,
  digest_algorithm VARCHAR,
  verification VARCHAR DEFAULT NULL,
  sha1 VARCHAR DEFAULT NULL,
  FOREIGN KEY (observation_uuid) REFERENCES observations(uuid)
);

CREATE TABLE certificates (
  certificate_id integer PRIMARY KEY DEFAULT NEXTVAL('certificate_seq'),
  signature_id VARCHAR,
  sha256 VARCHAR DEFAULT NULL,
  issuer_sha256 VARCHAR DEFAULT NULL,
  cert_version VARCHAR DEFAULT NULL,
  serial_number VARCHAR DEFAULT NULL,
  issuer_name VARCHAR DEFAULT NULL,
  subject_name VARCHAR DEFAULT NULL,
  issued_on VARCHAR DEFAULT NULL,
  expires_on VARCHAR DEFAULT NULL,
  signed_using VARCHAR DEFAULT NULL,
  RSA_key_size VARCHAR DEFAULT NULL,
  basic_constraints VARCHAR DEFAULT NULL,
  key_usage VARCHAR DEFAULT NULL,
  ext_key_usage VARCHAR DEFAULT NULL,
  certificate_policies VARCHAR DEFAULT NULL,
  FOREIGN KEY (signature_id) REFERENCES signatures(signature_id)
);

CREATE VIEW aout_metadata AS
SELECT observation_uuid, aoutMachineType
FROM base_metadata
WHERE filetype = 'A.OUT big' OR filetype = 'A.OUT little';

CREATE VIEW coff_metadata AS
SELECT observation_uuid, coffMachineType
FROM base_metadata
WHERE filetype = 'COFF' OR filetype = 'XCOFF32' OR filetype = 'XCOFF64' OR filetype = 'ECOFF';

CREATE VIEW docker_metadata AS
SELECT observation_uuid, dockerSPDX
FROM base_metadata
WHERE filetype = 'DOCKER_GZIP' OR filetype = 'DOCKER_TAR';

CREATE VIEW elf_metadata AS
SELECT observation_uuid, OS, EI_CLASS, EI_DATA, EI_VERSION, EI_OSABI, EI_ABIVERSION, E_MACHINE, elfDependencies, elfRpath, elfRunpath, elfSoname, elfInterpreter, elfDynamicFlags, elfDynamicFlags1, elfGnuRelro, elfComment, elfNote, elfOsAbi, elfHumanArch, elfArchNumber, elfArchitecture, elfIsExe, elfIsLib, elfIsRel, elfIsCore
FROM base_metadata
WHERE filetype = 'ELF' OR filetype = 'Linux Kernel Image';

CREATE VIEW java_metadata AS
SELECT observation_uuid
FROM base_metadata
WHERE filetype = 'JAVACLASS' OR filetype = 'JAR' OR filetype = 'WAR' OR filetype = 'EAR' OR filetype = 'APK';

CREATE VIEW javascript_metadata AS
SELECT observation_uuid, jsLibraries
FROM base_metadata;

CREATE VIEW macho_metadata AS
SELECT observation_uuid, OS, numBinaries, binaries
FROM base_metadata
WHERE filetype = 'MACHOFAT' OR filetype = 'MACHOFAT64' OR filetype = 'EFIFAT' OR filetype = 'MACHO32' OR filetype = 'MACHO64' OR filetype = 'IPA' OR filetype = 'MACOS_DMG';

CREATE VIEW native_metadata AS
SELECT observation_uuid, nativeLibraries
FROM base_metadata
WHERE filetype = 'LLVM_BITCODE' OR filetype = 'LLVM_IR';

CREATE VIEW ole_metadata AS
SELECT observation_uuid, ole
FROM base_metadata
WHERE filetype = 'OLE' OR filetype = 'MSCAB' OR filetype = 'ISCAB' OR filetype = 'MSIX';

CREATE VIEW pe_metadata AS
SELECT observation_uuid, OS, peMachine, peOperatingSystemVersion, peSubsystemVersion, peSubsystem, peLinkerVersion, peImport, peIsExe, peIsDll, peIsClr, FileInfo, dllRedirectionLocal
FROM base_metadata
WHERE filetype = 'PE' OR filetype = 'Malformed PE' OR filetype = 'DOS';

CREATE VIEW rpm_metadata AS
SELECT observation_uuid, rpm
FROM base_metadata
WHERE filetype = 'RPM Package';

CREATE VIEW uboot_metadata AS
SELECT observation_uuid, uimage_header
FROM base_metadata
WHERE filetype = 'UIMAGE';

CREATE VIEW other_metadata AS
SELECT observation_uuid, description
FROM base_metadata
WHERE filetype = 'GZIP' OR filetype = 'BZIP2' OR filetype = 'XZ' OR filetype = 'TAR' OR filetype = 'RAR' OR filetype = 'ZIP' OR filetype = 'AR_LIB' OR filetype = 'OMF_LIB' OR filetype = 'ZLIB' OR filetype = 'CPIO_BIN big' OR filetype = 'CPIO_BIN little' OR filetype = 'CPIO_ASCII_OLD' OR filetype = 'CPIO_ASCII_NEW' OR filetype = 'CPIO_ASCII_NEW_CRC' OR filetype = 'ZSTANDARD' OR filetype = 'ZSTANDARD_DICTIONARY' OR filetype = 'ISO_9660_CD';

