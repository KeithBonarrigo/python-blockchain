import functools
import hashlib
from block import Block
from transaction import Transaction
from verification import Verification

import hash_util
import json

MINING_REWARD = 10

class Blockchain:

    def __init__(self, hosting_node_id):
        # Initializing our (empty) blockchain list
        self.__chain = []
        genesis_block = Block(0, '', [], 100, 0)
        self.chain = [genesis_block]
        self.__open_transactions = []
        self.load_data()
        self.hosting_node = hosting_node_id
        #self.owner = owner
        #blockchain = []
        #open_transactions = []
        #owner = 'Max'
        #participants = {'Max'}

    # def get_chain(self):
    #     return self.__chain[:]
    @property
    def chain(self):
        return self.__chain[:]

    @chain.setter
    def chain(self, val):
        self.__chain = val

    def get_open_transactions(self):
        return self.__open_transactions

    def load_data(self):
        #global blockchain
        #global open_transactions

        try:
            with open('blockchain.txt', mode='r') as f:
                file_content = f.readlines()
                blockchain = json.loads(file_content[0][:-1])
                updated_blockchain = []
                for block in blockchain:
                    # updated_block = {
                    #     'previous_hash': block['previous_hash'],
                    #     'index': block['index'],
                    #     'proof': block['proof'],
                    #     'transactions': [OrderedDict([('sender', tx['sender']), ('recipient', tx['recipient']), ('amount', tx['amount'])]) for tx in block['transactions']]
                    # }
                    #converted_tx = [OrderedDict([('sender', tx['sender']), ('recipient', tx['recipient']), ('amount', tx['amount'])]) for tx in block['transactions']]
                    converted_tx = [Transaction(tx['sender'], tx['recipient'], tx['amount']) for tx in block['transactions']]
                    updated_block = Block(block['index'], block['previous_hash'], converted_tx , block['proof'], block['timestamp'])
                    updated_blockchain.append(updated_block)
                self.chain = updated_blockchain
                open_transactions = json.loads(file_content[1])
                updated_open_transactions = []
                for tx in open_transactions:
                    #updated_transaction = OrderedDict([('sender', tx['sender']), ('recipient', tx['recipient']), ('amount', tx['amount'])])
                    updated_transaction = Transaction(tx['sender'], tx['recipient'], tx['amount'])
                    updated_open_transactions.append(updated_transaction)
                self.__open_transactions = updated_open_transactions
        except (IOError, IndexError):
            print("Handled exception")
        finally:
            print("Clean up")

    def save_data(self):
        try:
            with open('blockchain.txt', mode='w') as f:
                #saveable_chain = [block.__dict__ for block in blockchain]
                saveable_chain = [block.__dict__ for block in [Block(block_el.index, block_el.previous_hash, [tx.__dict__ for tx in block_el.transactions], block_el.proof, block_el.timestamp) for block_el in self.__chain]]
                f.write(json.dumps(saveable_chain))
                #f.write(json.dumps(blockchain))
                f.write('\n')
                saveable_open_transactions = [tx.__dict__ for tx in self.__open_transactions]
                #f.write(json.dumps(open_transactions))
                f.write(json.dumps(saveable_open_transactions))
        except:
            print('File saving failed')

    def proof_of_work(self):
        last_block = self.__chain[-1]
        last_hash = hash_util.hash_block(last_block)
        proof = 0
        while not Verification.valid_proof(self.__open_transactions, last_hash, proof):
            proof += 1
        return proof

    def get_balance(self, participant):
        #participant = self.hosting_node
        amount_sent = self.calculate_balance('sender', participant)
        amount_received = self.calculate_balance('recipient', participant)
        balance = amount_received - amount_sent
        return balance

    def get_last_blockchain_value(self):
        """ Returns the last value of the current blockchain. """
        if len(self.__chain) < 1:
                return None
        return self.__chain[-1]

        # This function accepts two arguments.
        # One required one (transaction_amount) and one optional one (last_transaction)
        # The optional one is optional because it has a default value => [1]


    def add_transaction(self, recipient, sender, amount=1.0):
        """ Append a new value as well as the last blockchain value to the blockchain.

        Arguments:
            :sender: The sender of the coins.
            :recipient: The recipient of the coins.
            :amount: The amount of coins sent with the transaction (default = 1.0)
        """
        transaction = Transaction(sender, recipient, amount)
        #transaction = OrderedDict([('sender', sender), ('recipient', recipient), ('amount', amount)])
        #sender_balance = self.get_balance(sender)
        if Verification.verify_transaction(transaction, self.get_balance):
            self.__open_transactions.append(transaction)
            #participants.add(sender)
            #participants.add(recipient)
            self.save_data()
            return True
        return False

    def mine_block(self, node):
        last_block = self.__chain[-1]
        hashed_block = hash_util.hash_block(last_block)
        #hashed_block = hash_util.hash_block(dict_block)
        proof = self.proof_of_work()
        # reward_transaction = {
        #     "sender":"MINING",
        #     "recipient":owner,
        #     "amount": MINING_REWARD
        # }
        print("my id is:")
        print(self.hosting_node)
        #reward_transaction = OrderedDict([('sender', 'MINING'), ('recipient', owner), ('amount', MINING_REWARD)])
        reward_transaction = Transaction('MINING', node, MINING_REWARD)

        copied_transactions = self.__open_transactions[:]
        copied_transactions.append(reward_transaction)
        #open_transactions.append(reward_transaction)
        # block = {
        #     'previous_hash': hashed_block,
        #     'index':len(blockchain),
        #     'transactions':copied_transactions,
        #     'proof':proof
        # }
        block = Block(len(self.__chain), hashed_block, copied_transactions, proof)
        self.__chain.append(block)
        self.__open_transactions = []
        self.save_data()
        return True

    def calculate_balance(self, mode, participant):
        #tx_to_return = [[tx['amount'] for tx in block['transactions'] if tx[mode] == participant] for block in blockchain]
        #tx_to_return = [[tx['amount'] for tx in block.transactions if tx[mode] == participant] for block in blockchain]
        if mode=='sender':
            #tx_to_return = [[tx.amount for tx in block.transactions if tx.mode == participant] for block in blockchain]
            tx_to_return = [[tx.amount for tx in block.transactions if tx.sender == participant] for block in self.__chain]
            return_value = functools.reduce( lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt)>0 else tx_sum + 0,tx_to_return, 0)

        if mode == 'recipient':
            tx_to_return = [[tx.amount for tx in block.transactions if tx.recipient == participant] for block in self.__chain]
            return_value = functools.reduce( lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt)>0 else tx_sum + 0,tx_to_return, 0)
            opens_to_return = [tx.amount for tx in self.__open_transactions if tx.sender == participant]
            open_return = sum(opens_to_return)
            return_value -= open_return

        print(mode + " " + str(participant) + ' balance of ' + str(return_value))
        return return_value









