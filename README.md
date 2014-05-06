CuBolt
======

### A cuwo plugin API

CuBold is a plugin API for the Cube World server cuwo extending it's features for plugin developers to make the usage of some features easier and more performant.

### Features

Currently CuBolt has the following features:
- Extended entity management
- Hostility management for entities

### Important notes

Be aware:
In order to achieve the best possible performance, CuBold injects some code into cuwo. Currently only the update routine is replaced, this should not break other plugins but it may as unusual things happen sometimes.

### Installation

<ol>
  <li>You need [cuwo](http://cuwo.org/#about) to use CuBolt.</li>
  <li>Download the source of CuBolt, you should get a folder named "cubolt"</li>
  <li>Place the "cubold" folder inside the scripts directory of cuwo.</li>
  <li>Edit cuwo's base.py (it's inside the config directory). You need to adapt the scripts entry to this form:<br>
```python
scripts = ['log', 'cw', # other scripts following
]
```</li>
  <li>Launch the server, it should say something like
```
[CB] Initializing CuBolt...
[CB] Done (Xs).
```</li>
</ol>

### Usage
(coming soon)
