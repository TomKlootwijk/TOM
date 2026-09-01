# Archive and manifest policy

`MANIFEST_v0.5.json` hashes every file present at manifest creation except itself and `SHA256SUMS.txt`. `SHA256SUMS.txt` then hashes all files except itself, including the JSON manifest. The release ZIP is created from the quiescent project tree with normalized timestamps and the `-X` metadata-stripping option. ZIP integrity is tested after creation; those post-archive logs are distributed beside, rather than inside, the immutable archive.

Verification commands:

```bash
cd nhdf_ccd_v0_5
sha256sum -c SHA256SUMS.txt
zip -T ../NHDF_CCD_Cradle_to_Grave_v0.5.zip
qpdf --check NHDF_CCD_Cradle_to_Grave_v0.5.pdf
```
