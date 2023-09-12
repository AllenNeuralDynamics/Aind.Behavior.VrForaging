# aind-vr-foraging

- [aind-vr-foraging](#aind-vr-foraging)
  - [Deployment](#deployment)
  - [Prerequisites](#prerequisites)
  - [Notes on data-schema regeneration](#notes-on-data-schema-regeneration)

## Deployment

To deploy the Bonsai code, run `./bonsai/setup.cmd`. This small script will download and regenerate the current bonsai environment ([see tutorial for further details.](https://bonsai-rx.org/docs/articles/environments.html))

---

## Prerequisites

These should only need to be installed once on a fresh new system, and are not required if simply refreshing the install or deploying to a new folder.

- Windows 10 or 11
- [Visual Studio Code](https://code.visualstudio.com/) (highly recommended for editing code scripts and git commits)
- [Git for Windows](https://gitforwindows.org/) (highly recommended for cloning and manipulating this repository)
- [.NET Framework 4.7.2 Developer Pack](https://dotnet.microsoft.com/download/dotnet-framework/thank-you/net472-developer-pack-offline-installer) (required for intellisense when editing code scripts)
- [Visual C++ Redistributable for Visual Studio 2012](https://www.microsoft.com/en-us/download/details.aspx?id=30679) (native dependency for OpenCV)
- [FTDI CDM Driver 2.12.28](https://www.ftdichip.com/Drivers/CDM/CDM21228_Setup.zip) (serial port drivers for HARP devices)
- [Spinnaker SDK 1.29.0.5](https://www.flir.co.uk/support/products/spinnaker-sdk/#Downloads) (device drivers for FLIR cameras)
  - On FLIR website: `Download > archive > 1.29.0.5 > SpinnakerSDK_FULL_1.29.0.5_x64.exe`
- [NI-DAQmx 19.0](https://www.ni.com/en-gb/support/downloads/drivers/download.ni-daq-mx.html#301173) (drivers for NI-DAQ devices)

---

## Notes on data-schema regeneration

 1 - Install [bonsai.sgen dotnet tool](https://github.com/bonsai-rx/sgen)

 2 - Run `bonsai.sgen` targeting the root schema in `src/DataSchemas`. E.g.:

```cmd
bonsai.sgen --schema "src\DataSchemas\aind-vr-foraging-session.json" --namespace AindVrForagingDataSchema --root AindVrForagingSession --output "src\Extensions\AindVrForagingSession.cs" --serializer NewtonsoftJson YamlDotNet
```

To regenerate the loggers, use:

```cmd
bonsai.sgen --schema "src\DataSchemas\aind-vr-foraging-logging.json" --namespace AindVrForagingDataSchema.Logging --root AindVrForagingLogging --output "src\Extensions\AindVrForagingLogging.cs" --serializer NewtonsoftJson YamlDotNet
``
