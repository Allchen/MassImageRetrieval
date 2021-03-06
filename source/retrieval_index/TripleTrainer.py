#-*- coding:utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os, sys, copy
proj_dir = "/".join(os.path.abspath(__file__).split("/")[:-3])
sys.path.insert(0, proj_dir)

import importlib
importlib.reload(sys)

import numpy as np
import tensorflow as tf

from source.retrieval_index.TripleModel import TripleModel
from source.retrieval_index.DataSampler import DataGenerator


class TripleTrainer:
    def __init__(self, sample_creator=None, triple_model=None):
        self.sample_creator = sample_creator
        self.triple_model = triple_model

        self.batch_size = 2000
        self.epochs = 100
        self.plot_size = 60000
        self.is_update = True

        self.xy = None

        self.sess = tf.InteractiveSession()
        self.saver = None
        self.log_save_dir = "./log/"

    def reload_model(self):
        if os.path.exists(self.log_save_dir + "checkpoint"):
            ckpt = tf.train.get_checkpoint_state(self.log_save_dir)
            if ckpt and ckpt.model_checkpoint_path:
                self.saver.restore(self.sess, ckpt.model_checkpoint_path)

    def start_train(self):
        self.triple_model.build_model()
        # total_loss = self.triple_model.total_loss
        # train_step = tf.train.AdamOptimizer(0.01).minimize(total_loss)

        triple_loss = self.triple_model.triple_loss_val
        classify_loss = self.triple_model.classify_loss_val
        hash_loss = self.triple_model.hash_loss_val

        train_triple_step = tf.train.AdamOptimizer(0.01).minimize(triple_loss)
        train_classify_step = tf.train.AdamOptimizer(0.01).minimize(classify_loss)
        train_hash_step = tf.train.AdamOptimizer(0.01).minimize(hash_loss)

        tf.global_variables_initializer().run()

        self.saver = tf.train.Saver(max_to_keep=3)

        self.reload_model()
        try:
            for epoch_id in range(0, self.epochs):
                epoch_loss_vals = list()
                for iter in range(0, self.sample_creator.train_sample_length//self.batch_size):
                    x_a, x_p, x_n, y_a, y_p, y_n = self.sample_creator.get_triples_data(self.batch_size, is_update=self.is_update)
                    y_label = np.concatenate([y_a, y_p, y_n])
                    _, _, _, loss1, loss2, loss3, acc = self.sess.run(
                        [train_triple_step,
                         train_classify_step,
                         train_hash_step,
                         triple_loss,
                         classify_loss,
                         hash_loss,
                         self.triple_model.accuracy],
                        feed_dict={
                            self.triple_model.anchor_input: x_a,
                            self.triple_model.positive_input: x_p,
                            self.triple_model.negative_input: x_n,
                            self.triple_model.all_y_true_label: y_label
                        })
                    epoch_loss_vals.append([loss1, loss2, loss3, acc])
                    if iter % 10 == 0:
                        print("\titer: {}, triple loss: {}, classify loss: {}, hash loss: {}, acc: {}".format(iter, *np.mean(epoch_loss_vals, axis=0)))
                print("{} epoch, mean loss {}".format(epoch_id, np.mean(epoch_loss_vals, axis=0)))

                # predict and show the results
                self.predict_all_samples()
                self.sample_creator.cb_update_total_predict_values(self.xy)
                self.sample_creator.show_predict_result(self.plot_size, is_save_predict=True)

                # self.show_model_resuls(epoch_id)
                self.save_model_log(epoch_id)
        except KeyboardInterrupt:
            self.save_model_log()

    def save_model_log(self, epoch_id=None):
        if not os.path.isdir(self.log_save_dir):
            os.makedirs(self.log_save_dir)
        if epoch_id is not None:
            self.saver.save(self.sess, self.log_save_dir + "model.ckpt",
                            global_step=epoch_id)
        else:
            self.saver.save(self.sess, self.log_save_dir + "model.ckpt")

    def predict_all_samples(self):
        self.xy = self.sess.run(self.triple_model.anchor_out, feed_dict={
            self.triple_model.anchor_input: self.sample_creator.X_train
        })


if __name__ == '__main__':
    sample_creator = DataGenerator(dataset_name="mnist")

    triple_model = TripleModel()

    triple_trainer = TripleTrainer(sample_creator, triple_model)
    triple_trainer.start_train()
