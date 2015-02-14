CuBolt
======

### A cuwo plugin API

CuBolt is a plugin API for the Cube World server cuwo extending it's features for plugin developers to make the usage of some features easier and more performant.

### Features

Currently CuBolt has the following features:
- Extended entity management
- Hostility management for entities
- world editing features such as setting blocks

### Important notes

Be aware:
In order to achieve the best possible performance, CuBold injects some code into cuwo. This may break some scripts. A list of things that will cause problems can be found [here](https://github.com/UserXXX/CuBolt/wiki/Notes-for-developers).

### Installation

<ol>
  <li>You need cuwo(http://cuwo.org/#about) to use CuBolt.</li>
  <li>Download the source of CuBolt, you should get a folder named "cubolt"</li>
  <li>Place the "cubold" folder inside the scripts directory of cuwo.</li>
  <li>Edit cuwo's base.py (it's inside the config directory). You need to adapt the scripts entry to this form:<br>
scripts = ['log', 'cubold', # other scripts following<br>
]
</li>
  <li>Launch the server, it should say something like<br>
[CB] Initializing CuBolt...<br>
[CB] Done (Xs).
</li>
</ol>

### Usage

CuBolt represents an programming interface that makes some things much easier. All you need can be found on this picture:
![CuBold UML diagram](https://dl.dropboxusercontent.com/u/79973663/CuBolt/CuBolt%20API.png "CuBold UML diagram")
