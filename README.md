## Amun

Amun was the first python-based low-interaction honeypot, following the concepts of Nepenthes but extending it with
more sophisticated emulation and easier maintenance.

## Requirements

* Pyhon >= 2.6 (no Python3 support yet)
* (optional) Python Psyco (available at http://psyco.sourceforge.net/)
* (optional) MySQLdb if submit-mysql or log-mysql is used
* (optional) psycopg2 if log-surfnet is used

## Installation

* Clone Git repository: `git clone https://github.com/zeroq/amun.git`
* Edit Amun main configuration file: `vim conf/amun.conf`
  * for example set the ip address for Amun to listen on (0.0.0.0 to listen on all)
  * enable or disbale vulnerability modules as needed
* start the Amun by issuing: `./amun_server`

## Tips and Tricks

In case you encounter problems with too many open files due to a lot of attackers hitting your honeypot at the same time, the following settings can be adjusted:

* To increase the maximum number of open files on Linux:
  * `echo "104854" > /proc/sys/fs/file-max`
  * `ulimit -Hn 104854`
  * `ulimit -n 104854`
* To increase the maximum number of open files on BSD:
  * `sysctl kern.maxfiles=104854`
  * `ulimit -Hn 104854`
  * `ulimit -n 104854`

## Logging

All logging information are stored in the "logs" subdirectory of your Amun installation. Following log files will be created:

* amun\_server.log
  * contains general information, errors, and alive messages of the amun server
* amun\_request\_handler.log
  * contains information about unknown exploits and not matched exploit stages
* analysis.log
  * contains information about manual shellcode analysis (performed via the -a option)
* download.log
  * contains information about all download modules (ftp, tftp, bindport, etc...)
* exploits.log
  * contains information about all exploits that where triggert
* shellcode_manager.log
  * contains information and errors of the shellcode manager
* submissions.log
  * contains information about unique downloads
* successfull_downloads.log
  * contains information about all downloaded malware
* unknown_downloads.log
  * contains information about unknown download methods
* vulnerabilities.log
  * contains information about certain vulnerability modules

## Parameters

Amun can be executed with `-a` parameter to analyse a given file for known shellcode instead of running the honeypot. 

# Amun SSH Extensions

Amun is a Python-based low-interaction honeypot inspired by Nepenthes. It extends capabilities with more sophisticated emulation and easier maintenance. This version includes SSH-specific extensions to enhance interaction using a Large Language Model (LLM).

---

## Requirements

### Core Amun Honeypot
- **Python 2.6 or 2.7** (Python 3 is not supported for the core honeypot).
- **Optional**:
  - [Psyco](http://psyco.sourceforge.net/) for performance improvement (Python 2.x only).
  - **MySQLdb**: Required if `submit-mysql` or `log-mysql` is enabled.
  - **psycopg2**: Required if `log-surfnet` is enabled.

### SSH Extensions
- **Python 3** for `llm_shell.py` and `shellcodeAnalyzer.py`.

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/MistContinousDoing/Amun-ssh.git
   cd Amun-ssh
## Running guidance
Step 1: Prepare SSH Extensions (Python 3)
Create and activate a Python 3 virtual environment:
```bash
python3 -m venv llm_env
source llm_env/bin/activate
```
Step2: Run the SSH-related scripts:
```bash
python3 shellcodeAnalyzer.py
python3 llm_shell.py
```
Step 3: Start the Core Honeypot (Python 2.7)
Open a new terminal and run the core honeypot:
```bash
sudo python2.7 amun_server.py
```
