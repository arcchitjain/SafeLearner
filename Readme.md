# SafeLearner

This is a documentation on how to install and use the codes of **SafeLearner**.
It is licensed under  [Apache-2.0 license](https://github.com/arcchitjain/SafeLearner/blob/master/LICENSE).


## Dependencies
* Python 3.6
* PostgreSQL (version > 9.1)
* Java


## Installation
### Use *pipenv*  to install the following required python packages
1. Install *pipenv* first, if not already installed:
```
pip install pipenv
```
2. Clone this repository to your local machine
```
git clone -b AKBC19 --single-branch https://github.com/arcchitjain/SafeLearner.git
```
3. Move to this repository and install all the required packages:
```
pipenv install
```
This should install the following packages in a virtual environment of Python 3.6 for you:
* *ad*
* *nltk*
* *problog*
* *psycopg2*
* *sqlparse*
* *sympy*

4. Now, to activate the virtual environment, run the following:
```
pipenv shell
```
5. Steps to install *Prover9* - Python module for *nltk* <br>
*Prover9* is a non-standard package which gets installed by the following steps:
	1. Download  LADR-2009-11A.tar.gz from [https://www.cs.unm.edu/~mccune/prover9/download/](https://www.cs.unm.edu/~mccune/prover9/download/)
	2. Extract its files and run ‘make all’
	3. Copy all the files created in ‘bin’ folder to any of the following locations:
``` 
    /usr/local/bin/prover9 
    /usr/local/bin/prover9/bin
    /usr/local/bin
    /usr/bin
    /usr/local/prover9
    /usr/local/share/prover9
```

## Input Parameters

**SafeLearner** supports many variations of its main algorithm:

Argument | Description
-------|------
`file` | Input file with location (Required Argument)
`-t` | Target predicate with arity (Eg: -t "coauthor/2")
`-l` | Maximum rule length; Maximum number of total literals in a rule (including head)
`--log` | Logger file with location 
`-v` | Verbosity level of the log (Use -v -v -v for full verbosity)
`-s` | Specify scoring/loss function for SGD (Default: "cross_entropy", Other options: "accuracy", "squared_loss")
`--lr` | Specify earning rate parameter of SGD
`-i` | Specify number of iterations of SGD
`-c` | Cost of misclassification for negative examples (Default: 1.0)
`-q` | Input -q to denote an input file with facts enclosed in double quotes
`--minpca` | Minimum PCA Confidence Threshold for *Amie+*
`--minhc` | Minimum Standard Confidence Threshold for *Amie+*
`-r` | Allow recursive rules to be learned
`-a` | Specify maximum number of *Amie+* to be considered as candidate rules
`-d` | Disable/ignore typing of predicates while pruning *Amie+* rules
`--db_name` | Specify the name of the database to be used	
`--db_user` | Specify the username that can access the database
`--db_pass` | Specify the password to access the database
`--db_localhost` | Specify the localhost to can access the database


## Example

You need to create a PostgreSQL Database first before running **SafeLearner**:
```
psql
CREATE DATABASE test_dbname;
\q
```
This creates an empty database in *psql* server on your machine.  Now, in the following command,  replace 'test_dbuser' with the username of your *psql* server and add password and localhost name if required.
```
python3 safelearner.py Data/Test-Coauthor/illustrative_example.pl --log test.log -v -v -v -i 10000 --lr 0.00001 --minpca 0.00001 --minhc 0.00001 --db_name test_dbname --db_user test_dbuser
```
Running this command will execute **SafeLearner** on a small toy dataset and would ensure that it had got installed correctly.


## Credits

**SafeLearner** is based on the work, titled as **Scalable Rule Learning in Probabilistic Knowledge Bases**, by Arcchit Jain, Tal Fredman, Ondrej Kuzelka, Guy Van den Broeck, and Luc De Raedt. The work  was accepted and published in the 1st Conference on [Automated Knowledge Base Construction (AKBC) 2019](http://akbc.ws/) and held at the University of Massachusetts from 20 - 22 May 2019. 
More details about the paper can be found at [https://openreview.net/forum?id=HkyI-5667](https://openreview.net/forum?id=HkyI-5667)

**SafeLeaner** code was implemented by Arcchit Jain.

## Acknowledgements

The authors express their sincere regards to Anton Dries and Sebastijan Dumancic for their invaluable input, and the reviewers for their useful suggestions. This work has received funding from the European Research Council under the European Union's Horizon 2020 research and innovation programme (#694980 SYNTH: Synthesising Inductive Data Models), from the various grants of Research Foundation - Flanders, NSF grants #IIS-1657613, #IIS-1633857, #CCF-1837129, NEC Research, and a gift from Intel.

## Contact

Arcchit Jain <br>
arcchit.jain@cs.kuleuven.be <br>
Declarative Languages and Artificial Intelligence (DTAI) Research Group <br>
Department of Computer Science <br>
KU Leuven <br>