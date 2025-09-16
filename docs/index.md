# Revolution EDA Documentation

Welcome to the documentation of Revolution EDA! This comprehensive guide is designed to provide you with all the information you need to effectively use our software for your electronic design needs.

Our electronic design automation package is a powerful tool that allows designers to create, simulate and verify complex electronic circuits and systems. With a user-friendly interface, advanced simulation capabilities and a wide range of design tools, our package offers a complete solution for designing and optimizing electronic circuits.

This documentation is organized to take you through the different stages of the design process, from creating a new project to generating a final output. Each section provides detailed information on the features and functionalities of our package, along with step-by-step instructions and examples to help you get started quickly.

Whether you are a novice designer or an experienced professional, our electronic design automation package offers the flexibility and power you need to create sophisticated electronic designs. We hope that this documentation will be a valuable resource for you as you explore and use our software.

------

### [Config Editor](./configEditor.md)

Revolution EDA also offers the ability to create a *config* view to control the netlisting process. Using a config view, the designer can decide which view will be used in the netlist process, e.g. schematic, veriloga, spice or symbol. Over time other hardware description languages will be also incorporated.

------

### [Installation](./installation.md)

Revolution EDA offers a few different methods for installation. Whether using a wheel from PyPi repository, or downloading a binary package or cloning the source repository from GitHub, the installation process is easy and intuitive.

------

### [Layout Editor](./layoutTutorial.md)

Layout editor is a recent addition to Revolution EDA and allows the basic editing functions necessary in the physical layout of custom integrated circuits. Currently, the layout editor can create:

------

### [Main Window](./revedaMainWindow.md)

Revolution EDA window is the first window an user interacts. At the moment, `Tools`, `Options` and `Help` menus are usable. Revolution EDA main window also includes a Python REPL interpreter. Python statements can be input at `>` prompt. Revolution EDA API is not yet stable but the user can still access all the power of a Python interpreter.

------

### [Schematic Editor](./schematicTutorial.md)

Schematic editor is used to instantiate symbol and define the nets that connect them.. The schematic editor is where the circuit design process begins. The schematic editor window is very similar to symbol editor window:

------

### [Symbol Editor](./symbolTutorial.md)

Symbol Editor is where the schematic representation of a basic circuit component, such as an inductor, capacitor or even an entire circuit can be created to be later used in the schematic editor.