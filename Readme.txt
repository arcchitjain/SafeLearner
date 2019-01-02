This is a documentation on how to install and use the codes for 'SafeLearner':

1. Check Pre-Requisites:
	a. Python 2.7: 
		Essential: problog, psycopg2, ad, nltk (Prover9)
		Standard : logging, copy, sys, argparse, os, random, time, subprocess
		Optional : scipy, pickle, numpy. 
			You may need to comment out few lines of code or change some parameters, if you are running without optional packages.
	b. Java
	c. PostgreSQL (Preferably > 9.1)

	>> Steos to install ‘Prover9’ - Python module for ‘nltk’
			This is a non-standard package which gets installed by the following steps:
				i)  Download  LADR-2009-11A.tar.gz from https://www.cs.unm.edu/~mccune/prover9/download/
				ii) Extract it files and run ‘make all’
				iii)Copy all the files created in ‘bin’ folder to any of the following locations:
						/usr/local/bin/prover9
						/usr/local/bin/prover9/bin
						/usr/local/bin
						/usr/bin
						/usr/local/prover9
						/usr/local/share/prover9

2. Know your Input Parameters:
	  -h, --help            show this help message and exit
	  -1, --det-rules       learn deterministic rules
	  -m M                  parameter m for m-estimate
	  -b BEAM_SIZE, --beam-size BEAM_SIZE
	                        size of beam for beam search
	  -p P, --significance P
	                        rule significance threshold
	  -l L, --length L      maximum rule length
	  -v                    increase verbosity (repeat for more)
	  --symmetry-breaking   avoid symmetries in refinement operator
	  -t TARGET, --target TARGET
	                        specify predicate/arity to learn (overrides settings file)
	  --log LOG             write log to file
	  -c, --closed-world    Closed World Indicator (Input -c to learn on closed world setting)
	  -g GLOBAL_SCORE, --global-score GLOBAL_SCORE
	                        specify global scoring function as either 'accuracy' or 'cross_entropy' (Default is 'cross_entropy')
	  -o OPTIMIZATION_METHOD, --optimization-method OPTIMIZATION_METHOD
	                        specify optimization method of lambda as either 'batch' or 'incremental' (Default is 'incremental')
	  -r CANDIDATE_RULES, --candidate-rules CANDIDATE_RULES
	                        specify generation method of candidate rules as either 'probfoil' or 'amie' (Default is 'amie')
	  -w COST, --cost COST  Misclassification Cost for negative examples
	  --minpca MINPCA       Minimum PCA Confidence Threshold for Amie
	  --minhc MINHC         Minimum Standard Confidence Threshold for Amie
	  -q, --quotes          Input -q to denote an input file with facts enclosed in double quotes
	  --ssh                 Input --ssh if the code is running on PINACS/HIMECS
	  --cwLearning          Input --cwLearning for learning rule weights with SGD in Closed World
	  -i ITERATIONS, --iterations ITERATIONS
	                        Number of iterations of SGD
	  -a MAXAMIERULES, --maxAmieRules MAXAMIERULES
	                        Maximum number of candidate rules to be learned from AMIE
	  -d, --disableTypeConstraints
	                        Input -d to ignore type constraints for learned rules
	  --lr1 LR1             Learning Rate for Rule Weights
	  --lr2 LR2             Learning Rate for Rule Weights

3. Example of commands:
	python probfoil.py Data/Test-Coauthor/test_full.pl --log test.log -v -v -v
	python probfoil_fast.py Data/Exp3-ScalingUp/NELL_1115_v3.pl --log apil_1115_cw.log -v -v -v -i 10000 -q -t athleteplaysinleague/2 --ssh --minpca 0.01 --minhc 0.01 --cwLearning
	python probfoil_fast.py Data/Exp3-ScalingUp/yago.pl -t iscitizenof/2 --log yago_ico.log -v -v -v --ssh -q -i 10000 --disableTypeConstraints --lr1 0.001 --lr2 0.0001 -a 3 --minpca 0.00001 --minhc 0.00001

4. Difference between probfoil.py and probfoil_fast.py:
	'probfoil.py' also outputs the scores associated with the hypothesis. It computes the loss function at various intervals during SGD and picks the best paramters.
	'probfoil_fast.py' only performs operations on one example at a time. But doesn't do operations associated with all the data like 1) looping over all the xamples, 2) calculating scores of hypothesis on the examples, and 3) calculating the full loss function on the examples.

5. Credits:
	The algorithm is based on the work of Luc De Raedt, Ondrej Kuzelka, Guy Van den Broeck, Tal Fredman and Arcchit Jain. It was implemented by Arcchit Jain.
	https://openreview.net/forum?id=HkyI-5667
	
6. Contact Details:
	Arcchit Jain
	arcchit.jain@cs.kuleuven.be
	Declarative Languages and Artificial Intelligence Research Group
	Department of Computer Science
	KU Leuven
