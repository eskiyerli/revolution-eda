# Installation

Revolution EDA can be used in Windows, Mac and Linux systems. There are a few different methods of installation depending on the user preference and experience.

## Cloning from Github RevEDA Release repository

Revolution EDA release repository is in GitHub and is regularly updated with the latest code.
The released code is licensed with Mozilla Public License v2 modified with Commons Clause. This
basically means that the users are able to use and modify the code as they wish but they cannot
sell it.

There are a few different methods to clone the repository:

1. Command line: `git clone https://github.com/eskiyerli/revedaRelease.git`
2. Using Github CLI: `gh repo clone eskiyerli/revedaRelease`
3. Using Github Desktop:  Under `File` menu, find clone `Clone Repository...` item and click.
   Choose `Github.com` tab and enter repository URL:  <https://github.com/eskiyerli/revedaRelease>

<img src="assets/image-20230209082047928.png" alt="Github Desktop Dialog" class="small-image"  />

## Download a release from RevEDA Release repository

Revolution EDA is also released has single binary packages created for Windows and Linux
using [Nuitka](https://nuitka.net) . According to Nuitka documentation,

> Nuitka is the optimizing Python compiler written in Python that creates executables that run
> without an need for a separate installer. Data files can both be included or put alongside.

These binaries can be found in [Revolution EDA Release](https://github.com/eskiyerli/revedaRelease/releases). The current
version is tagged as version 0.6.2 and can be found at (<https://github.com/eskiyerli/revedaRelease/releases/tag/v0.6.2> . Windows version is a single executable called `reveda.exe` and Linux executable is named `reveda.bin`. Note that Windows might warn you about if you want to run it. If you want to try to software, you should answer `yes`. For Linux version, you should make it executable by issuing `chmod +x reveda.bin`
command. Note that the binaries created by Nuitka is not guaranteed by the Revolution EDA.

## Download from PyPi Repository

Revolution EDA is also available as a downloadable package in PyPi repository. Use `pip`
command to download and install: `pip install revolution-eda`.

Regardless of the installation method, you can start Revolution EDA with `reveda` command.
