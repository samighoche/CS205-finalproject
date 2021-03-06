import sys
import os.path
sys.path.append(os.path.join('..', 'util'))

import set_compiler
set_compiler.install()

import pyximport
pyximport.install()

import numpy as np

import tfidf_cython as tfidf

from timer import Timer

def print_t(t, string) :
  print "Time for " + string + ": " + str(t.interval)

def init_globals(N=4, use_AVX = False, hash_size = 64, n_locks = 1) :
  '''
  Load questions into memory
  '''
  global AVX_f, size, lock_t, num_locks
  with Timer() as t :
    tfidf.init_globals(N)
  print_t(t, "Initialization")
  AVX_f = use_AVX
  assert(hash_size == 64 or hash_size == 32)
  size = hash_size
  num_locks = n_locks

  print "Using {0} threads".format(N)

  if use_AVX :
    print "Using AVX"

  print "Using {0} hash size".format(hash_size)

  print "Using {0} locks".format(n_locks)

def load_questions(questions) :
  '''
  Load questions into memory
  '''
  with Timer() as t :
    tfidf.load_questions(np.array(questions))
  print_t(t, "load_questions")

def load_indices(indices) :
  '''
  Load word indices into memory
  '''
  global num_keys, AVX_f
  num_keys = len(indices)
  if AVX_f :
    num_keys = num_keys if num_keys % 8 == 0 else num_keys + 8 - num_keys % 8
  with Timer() as t :
    for (key, value) in indices :
      tfidf.load_index(key.encode('utf-8', 'ignore'), value)
  print_t(t, "load_indices")

def init_tfs() :
  '''
  Create Term Frequencies for questions
  '''
  global num_keys
  with Timer() as t :
    tfidf.init_tfs(num_keys)
  print_t(t, "init_tfs")

def create_tfs() :
  '''
  Create Term Frequencies for questions
  '''
  global num_keys
  with Timer() as t :
    tfs = tfidf.create_tfs()
  print_t(t, "create_tfs")
  return tfs

def calculate_idf() :
  global num_keys, num_locks
  with Timer() as t:
    locks_ptr = tfidf.preallocate_locks(num_locks)
    idf = tfidf.calculate_idf(num_keys, locks_ptr, num_locks)
  print_t(t, "calculate_idf")
  return idf

def init_tfidfs() :
  global num_keys
  with Timer() as t:
    tfidfs = tfidf.init_tfidfs(num_keys)
  print_t(t, "int_tfidfs")

def calculate_tfidfs() :
  global num_keys, wAVX
  with Timer() as t:
    tfidfs = tfidf.calculate_tfidfs(num_keys, AVX_f)
  print_t(t, "calculate_tfidfs")
  return tfidfs

def calculate_tfidf(example_question) :
  global word_indices, idf_vector
  with Timer() as t :
    tf_vector = np.zeros(len(word_indices))
    for word in example_question :
      if word in word_indices :
        tf_vector[word_indices[word]] += 1
  print_t(t, "calculate_tfidf")
  return tf_vector * idf_vector

def calculate_cossim(example_question) :
  global tfidf_vectors, tfidf_norms
  with Timer() as t :
    example = calculate_tfidf(example_question)
    result = tfidf_vectors.dot(example) / (np.linalg.norm(example) * tfidf_norms)
  print_t(t, "calculate_cossim")
  return result

def calculate_simhashes() :
  global size
  with Timer() as t :
    if size == 64:
      simhashes = tfidf.calculate_simhashes64(size)
    # if size is 32
    else:
      simhashes = tfidf.calculate_simhashes32(size)
  print_t(t, "calculate_simhashes")
  return simhashes  

def calculate_distances():
  global size, simhashes
  with Timer() as t:
    if size == 64:
      tfidf.init_distances64()
    else:
      tfidf.init_distances32()
  print_t(t, "calculate_distances, init")
  with Timer() as t:
    if size == 64:
      distances = tfidf.calculate_distances64(size)
    else:
      distances = tfidf.calculate_distances32(size)
  print_t(t, "calculate distances, compute")
  return distances

def cleanup() :
  tfidf.cleanup()
  print "Done Cleanup"
