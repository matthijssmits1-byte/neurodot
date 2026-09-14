# Security and privacy

Neurodot is research software that processes microscopy files locally. The
authored application source does not upload images or results to a remote
service.

Do not attach confidential microscopy data, donor files, settings JSON, or log
files to a public issue. Logs and settings may contain filenames and local
filesystem paths. Reproduce a problem with non-sensitive data where possible.

Before distributing a portable build, review the bundled model, Imaris donor,
Python packages, and NVIDIA runtime files for applicable redistribution terms.
Public Windows executables should also be signed with a trusted code-signing
certificate.

Neurodot is intended for research use. Cell counts and generated Imaris scenes
must be scientifically validated and reviewed by a qualified operator before
they are used in analysis.
