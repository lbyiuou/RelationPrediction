from theano import tensor as T
import theano
import numpy as np
import pickle
import random
from theano.sandbox.rng_mrg import MRG_RandomStreams as RandomStreams
import imp

abstract_model = imp.load_source('abstract_model', 'code/experts/AbstractModel.py')
shared = imp.load_source('shared', 'code/experts/shared.py')

class Model(abstract_model.AbstractModel):

    predict_function = None
    embedding_width = 200
    number_of_negative_samples = 10
    regularization_parameter = 0.01

    positives_forward = None
    positives_backward = None
    srng = None
    
    def __init__(self):
        pass

    def predict(self, triplets):        
        e1s, e2s, rels = self.expand_triplets(triplets)
        return self.wrapper_predict(e1s, e2s, rels)

    
    def process_train_triplets(self, triplet_sample, all_triplets, disable_saving=False):
        new_labels = np.ones((len(triplet_sample) * (self.number_of_negative_samples + 1 ))).astype(np.float32) * -1
        new_indexes = np.tile(triplet_sample, (self.number_of_negative_samples + 1,1)).astype(np.int32)
        new_labels[:len(triplet_sample)] = 1

        if self.positives_forward is None:
            self.positives_forward, self.positives_backward = self.generate_positive_sample_dictionaries(all_triplets)

        number_to_generate = len(triplet_sample)*self.number_of_negative_samples
        choices = np.random.binomial(1, 0.5, number_to_generate)

        total = range(self.n_entities)

        for i in range(self.number_of_negative_samples):
            for j, triplet in enumerate(triplet_sample):
                index = i*len(triplet_sample)+j

                if choices[index]:
                    positive_objects = self.positives_forward[triplet[0]][triplet[1]]

                    found = False
                    while not found:
                        sample = random.choice(total)
                        if True: #sample not in positive_objects:
                            new_indexes[index+len(triplet_sample),2] = sample
                            found = True
                else:
                    positive_subjects = self.positives_backward[triplet[2]][triplet[1]]

                    found = False
                    while not found:
                        sample = random.choice(total)
                        if True: #sample not in positive_subjects:
                            new_indexes[index+len(triplet_sample),0] = sample
                            found = True

        if disable_saving:
            self.positives_forward = None
            self.positives_backward = None

        return new_indexes, new_labels

    def generate_positive_sample_dictionaries(self, triplets_in_kb):
        positives_forward = {}
        positives_backward = {}
        for triplet in triplets_in_kb:
            if triplet[0] not in positives_forward:
                positives_forward[triplet[0]] = {triplet[1] : [triplet[2]]}
            else:
                if triplet[1] not in positives_forward[triplet[0]]:
                    positives_forward[triplet[0]][triplet[1]] = [triplet[2]]
                else:
                    positives_forward[triplet[0]][triplet[1]].append(triplet[2])

            if triplet[2] not in positives_backward:
                positives_backward[triplet[2]] = {triplet[1] : [triplet[0]]}
            else:
                if triplet[1] not in positives_backward[triplet[2]]:
                    positives_backward[triplet[2]][triplet[1]] = [triplet[0]]
                else:
                    positives_backward[triplet[2]][triplet[1]].append(triplet[0])

        return positives_forward, positives_backward
    

    '''
    def generate_corrupted_entries(self, triplets_to_corrupt, triplets_in_kb, arr_to_mod, generate_new_dicts=False):
        if generate_new_dicts:
            self.positives_forward, self.positives_backward = self.generate_positive_sample_dictionaries(triplets_in_kb)

        number_to_generate = len(triplets_to_corrupt)*self.number_of_negative_samples
        choices = np.random.binomial(1, 0.5, number_to_generate)

        total = range(self.n_entities)

        for i in range(self.number_of_negative_samples):
            for j, triplet in enumerate(triplets_to_corrupt):
                index = i*len(triplets_to_corrupt)+j

                if choices[index]:
                    positive_objects = self.positives_forward[triplet[0]][triplet[1]]

                    found = False
                    while not found:
                        sample = random.choice(total)
                        if sample not in positive_objects:
                        left_entries.append(sample)
                    
                
        for i,triplet in enumerate(triplets_to_corrupt):
            positive_subjects = self.positives_backward[triplet[2]][triplet[1]]
            positive_objects = self.positives_forward[triplet[0]][triplet[1]]

            # This may be ineffective if there exists an element with a relation to MANY other elements.
            # For now, just run las vegas:

            right_entries = []
            while len(right_entries) < number_of_negative_samples:
                sample = random.choice(total)
                if sample not in positive_objects and sample not in right_entries:
                    right_entries.append(sample)

            left_entries = []
            while len(left_entries) < number_of_negative_samples:
                sample = random.choice(total)
                if sample not in positive_subjects and sample not in left_entries:
                    left_entries.append(sample)
                    
            #negative_subject_space = np.setdiff1d(total, positive_subjects)
            #negative_object_space = np.setdiff1d(total, positive_objects)
            
            #print(len(negative_subject_space))
            left_entries_t[i] = left_entries
            right_entries_t[i] = right_entries
        
        return np.array(left_entries_t).astype(np.int32), np.array(right_entries_t).astype(np.int32)

    '''
    def expand_triplets(self, triplets):
        triplet_array = np.array(triplets).astype(np.int32)
        organized = np.transpose(triplet_array)
        return organized[0], organized[2], organized[1]
        
    def initialize_variables(self):
        embedding_initial = np.random.randn(self.n_entities, self.embedding_width).astype(np.float32)
        #shared.glorot_initialization(self.n_entities+1, self.embedding_width)

        relation_initial = np.random.randn(self.n_relations, self.embedding_width).astype(np.float32)
        
        self.W_embedding = theano.shared(embedding_initial)
        self.W_relation = theano.shared(relation_initial)

    def get_weight_shapes(self):
        return ((self.n_entities,self.embedding_width), (self.n_relations, self.embedding_width))
        
    def get_weights(self):
        return (self.W_embedding,self.W_relation)
    
    def nonlinearity(self, v):
        return v #shared.lecunn_tanh(v)

    def get_update_list(self, update):
        #embedding_weight_length = T.sqrt(T.sum(update[0]*update[0], axis=1))
        #update[0] = update[0] / embedding_weight_length
        return [(self.W_embedding, update[0]),
                (self.W_relation, update[1])]

    def theano_batch_predict(self, e1s, e2s, rs):
        
        e1s_embed = self.W_embedding[e1s]
        e2s_embed = self.W_embedding[e2s]
        
        conv_relations = self.W_relation[rs]
        
        PT = e1s_embed * conv_relations * e2s_embed
        return T.nnet.sigmoid(T.sum(PT, axis=1))


    #def apply_embedding(self, v):
    #    return self.nonlinearity(shared.apply_transform_to_elements(v, self.W_embedding)) 

    def expand_relations(self, relation_id_list, with_dropout=False):
        '''
        if with_dropout:
            if self.srng is None:
                self.srng = RandomStreams(seed=12345)

            mask = self.srng.binomial(n=1, p=0.5, size=self.W_relation.shape, dtype='float32')
            W = self.W_relation * mask
        else:
            W = self.W_relation * 0.5
        '''

        W = self.W_relation
        one_hot_representation = T.extra_ops.to_one_hot(relation_id_list, self.n_relations)
        return T.dot(one_hot_representation, W)

    def theano_batch_loss(self, input_variable_list):
        #if self.srng is None:
        #    self.srng = RandomStreams(seed=12345)

        #mask = self.srng.binomial(n=1, p=0.5, size=self.W_relation.shape, dtype='float32')
        #W = self.W_relation * mask
        
        xs = input_variable_list[0]
        ys = input_variable_list[1]

        e1s = self.W_embedding[xs[:,0]]
        rs = self.W_relation[xs[:,1]]
        e2s = self.W_embedding[xs[:,2]]

        energies = T.sum(e1s * rs * e2s, axis=1)
        loss = T.nnet.softplus(-ys * energies).mean()
        regularizer = T.sqr(e1s).mean() + T.sqr(rs).mean() + T.sqr(e2s).mean()

        return loss + self.regularization_parameter * regularizer
    
    '''
    To be replaced by inherited methods:
    '''
    
    def save(self, filename):
        store_package = (self.W_embedding.get_value(),
                         self.W_relation.get_value(),
                         self.n_entities,
                         self.n_relations)

        store_file = open(filename, 'wb')
        pickle.dump(store_package, store_file)
        store_file.close()

    def load(self, filename):
        store_file = open(filename, 'rb')
        store_package = pickle.load(store_file)

        self.W_embedding = theano.shared(store_package[0])
        self.W_relation = theano.shared(store_package[1])
        self.n_entities = store_package[2]
        self.n_relations = store_package[3]
        
    
    def get_theano_input_variables(self):
        Xs = T.matrix('Xs', dtype='int32')
        Ys = T.vector('Ys', dtype='float32')

        return [Xs, Ys]
    
