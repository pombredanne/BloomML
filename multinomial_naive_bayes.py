from bloom_freqmap import BloomFreqMap
from pybloomfilter import BloomFilter
from time import time
from numpy import inf, log
from sklearn.metrics import f1_score

class MultinomiamNaiveBayes:
	def __init__(self, alpha, initial_capacity, error_rate):
		self.initial_capacity = initial_capacity
		self.error_rate = error_rate
		self.alpha = alpha
		
		#Tracks count | class for p(x|c)
		self.class_conditional_counts = {}#BloomFreqMap()
		
		#Tracks count all tokens | class for p(x|c)
		self.tokens_per_class = {}
		
		#Tracks count(class) for p(c)
		self.class_freqs = {}
		
		#Counts vocab size for smoothing
		self.token_type_bf = BloomFilter(capacity=initial_capacity, error_rate=error_rate)
		
		self.vocab_sizes = {}
		
		#Tracks the tokens in each class so that we can penalize unseen tokens
		#self.class_to_toks_bf = {}
		
		self.N = 0 #instance count
	
	def makeTokenFreqmap(self, tokens):
		f = {}
		get = f.get
		for token in tokens:
			f[token] = get(token, 0) + 1
		return f
		
	def fit(self, tokens, class_label):
		#if class_label not in self.class_to_toks_bf:
		#	self.class_to_toks_bf[class_label] = BloomFilter(capacity=self.initial_capacity, error_rate=self.error_rate)
		
		if class_label not in self.class_conditional_counts:
			self.class_conditional_counts[class_label] = BloomFreqMap(initial_capacity=self.initial_capacity, initial_error_rate=self.error_rate)
			self.vocab_sizes[class_label] = BloomFilter(capacity=self.initial_capacity, error_rate=self.error_rate)
			
		self.tokens_per_class[class_label] = self.tokens_per_class.get(class_label, 0) + len(tokens)
		tok_freqs = self.makeTokenFreqmap(tokens)
		conditional_counts_bf = self.class_conditional_counts[class_label]
		
		for token, token_freq in tok_freqs.iteritems():
			#self.class_to_toks_bf[class_label].add(token)
			self.token_type_bf.add(token)
			conditional_counts_bf.increment(token, by=token_freq)
			self.vocab_sizes[class_label].add(token)
			
		self.class_freqs[class_label] = self.class_freqs.get(class_label, 0) + 1
		self.N += 1
	
	def predict(self, tokens, tie_breaker='highest_freq', use_class_prior=True):
		
		N = self.N
		max_class, max_score = None, inf
		tok_freqs = self.makeTokenFreqmap(tokens)
		num_instances = sum((item[1] for item in self.class_freqs.iteritems()))
		for c, cf in self.class_freqs.iteritems():
			this_score = log(cf) - log(N) if use_class_prior else 0.0
			f_t_c = self.tokens_per_class[c]
			num_unseen = 0
			V = len(self.vocab_sizes[c])
			theta_denominator = log(f_t_c + V)
			for token, freq in tok_freqs.iteritems():
				count_in_c = self.class_conditional_counts[c].count(token)
				if count_in_c == 0:
					num_unseen += freq
					continue
				this_score += freq*(log(count_in_c + self.alpha) - theta_denominator)
			
			#Penalize unseen tokens
			this_score += num_unseen*(log(self.alpha) - log(theta_denominator))
			
			max_score, max_class = min((max_score, max_class), (this_score, c))
		
		return max_class, max_score

class TextToId:
	def __init__(self):
		self.str_to_id = {}
		self.id_to_str = {}
		
	def fit(self, l):
		for i in l:
			if i not in self.str_to_id:
				self.str_to_id[i] = len(self.str_to_id)
				self.id_to_str[len(self.str_to_id)-1] = i
				
	def transform(self, l):
		try:
			out = [self.str_to_id[s] for s in l]
		except:
			import code; code.interact(local=locals())
		return out
		
	def inverse(self, l):
		for id in l:
			yield self.id_to_str[str]
	
	def fit_transform(self, l):
		self.fit(l)
		return self.transform(l)
		
def test_nb():
	from os import walk
	print 'Testing nb'
	clf = MultinomiamNaiveBayes(0.5, 500000000, 0.0001)
	
	full_filenames = []
	#Get filenames
	for root, dirs, files in walk('data/20news-18828/'):
		for filename in files:
			full_filenames.append(root + '/' + filename)
	print len(full_filenames)
	
	from random import shuffle
	shuffle(full_filenames)
	from re import findall

	training_time = 0
	labels = []
	for filename in full_filenames:
		print 'Fitting', filename
		toks = findall('[A-Za-z]{3,}', open(filename).read())
		class_label = filename.rsplit('/', 2)[1]
		labels.append(class_label)
		
		t0 = time()
		clf.fit(toks, class_label)
		t1 = time()
		training_time += t1-t0
	
	#In-sample test error
	from sklearn.preprocessing import LabelEncoder
	le = TextToId()
	pred = []
	for filename in full_filenames:
		print 'Predicting', filename
		guess, score = clf.predict(findall('[A-Za-z]{3,}', open(filename).read()))
		pred.append(guess)
	le.fit(labels)
	
	print f1_score(le.transform(labels), le.transform(pred), pos_label=None, average='macro')
	print 'Done'

if __name__ == '__main__':
	test_nb()