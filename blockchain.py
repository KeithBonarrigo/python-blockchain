import functools
import hashlib
from block import Block
from transaction import Transaction
from utility.verification import Verification
from wallet import Wallet

from utility.hash_util import hash_block
import json
import requests

MINING_REWARD = 10

class Blockchain:

    def __init__(self, hosting_node_id, port):
        # Initializing our (empty) blockchain list
        self.__chain = []
        genesis_block = Block(0, '', [], 100, 0)
        self.chain = [genesis_block]
        self.__open_transactions = []
        self.hosting_node = hosting_node_id
        self.__peer_nodes = set()
        self.node_id = port
        self.load_data()
        self.resolve_conflicts = False

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
        """
        Loads blockchain - currently from text file
            :blockchain - object
            :open_transactions - object
            :peer_nodes - list
        """

        try:
            with open('blockchain-{}.txt'.format(self.node_id), mode='r') as f:
                file_content = f.readlines()
                blockchain = json.loads(file_content[0][:-1])
                updated_blockchain = []
                for block in blockchain:
                    converted_tx = [Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in block['transactions']]
                    updated_block = Block(block['index'], block['previous_hash'], converted_tx , block['proof'], block['timestamp'])
                    updated_blockchain.append(updated_block)
                self.chain = updated_blockchain
                open_transactions = json.loads(file_content[1][:-1])
                updated_open_transactions = []
                for tx in open_transactions:
                    #updated_transaction = OrderedDict([('sender', tx['sender']), ('recipient', tx['recipient']), ('amount', tx['amount'])])
                    updated_transaction = Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount'])
                    updated_open_transactions.append(updated_transaction)
                self.__open_transactions = updated_open_transactions
                peer_nodes = json.loads(file_content[2])
                self.__peer_nodes = set(peer_nodes)

        except (IOError, IndexError):
            print("Handled exception")
        finally:
            print("Clean up")

    def save_data(self):
        """saves blockchain data to text file - accepts no args"""
        try:
            print('saving')
            with open('blockchain-{}.txt'.format(self.node_id), mode='w') as f:
                saveable_chain = [block.__dict__ for block in [Block(block_el.index, block_el.previous_hash, [tx.__dict__ for tx in block_el.transactions], block_el.proof, block_el.timestamp) for block_el in self.__chain]]
                f.write(json.dumps(saveable_chain))
                f.write('\n')
                saveable_open_transactions = [tx.__dict__ for tx in self.__open_transactions]
                f.write(json.dumps(saveable_open_transactions))
                f.write('\n')
                f.write(json.dumps(list(self.__peer_nodes)))
        except:
            print('File saving failed')

    def proof_of_work(self):
        last_block = self.__chain[-1]
        last_hash = hash_block(last_block)
        proof = 0
        while not Verification.valid_proof(self.__open_transactions, last_hash, proof):
            proof += 1
        return proof

    def get_balance(self, sender=None):
        if sender == None:
            if self.hosting_node == None:
                return None
            participant = self.hosting_node
        else:
            participant = sender

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


    def add_broadcast_transaction(self, recipient, sender, signature, amount=1.0, is_receiving=True):
        """ Append a new value as well as the last blockchain value to the blockchain.
        Arguments:
            :sender: The sender of the coins.
            :recipient: The recipient of the coins.
            :amount: The amount of coins sent with the transaction (default = 1.0)
        """
        if self.hosting_node == None:
            return False
        transaction = Transaction(sender, recipient, signature, amount)
        if Verification.verify_broadcast_transaction(transaction, self.get_balance):
            self.__open_transactions.append(transaction)
            self.save_data()
            return True
        return False

    def add_transaction(self, recipient, sender, signature, amount=1.0, is_receiving=False):
        """ Append a new value as well as the last blockchain value to the blockchain.
        Arguments:
            :sender: The sender of the coins.
            :recipient: The recipient of the coins.
            :amount: The amount of coins sent with the transaction (default = 1.0)
        """
        if self.hosting_node == None:
            return False
        transaction = Transaction(sender, recipient, signature, amount)
        if Verification.verify_transaction(transaction, self.get_balance):
            self.__open_transactions.append(transaction)
            self.save_data()
            if not is_receiving:
                for node in self.__peer_nodes:
                    url = 'http://{}/broadcast-transaction'.format(node)
                    try:
                        with open('temp.txt', mode='w') as ff:
                            ff.write('url ' + url)
                            ff.write('\n')
                            ff.write('sender ' + sender)
                            ff.write('\n')
                            ff.write('recipient ' + recipient)
                            ff.write('\n')
                            ff.write('amount ' + str(amount))
                            ff.write('\n')
                            ff.write('signature ' + signature)
                            ff.write('\n')

                        response = requests.post(url, json={'sender': sender, 'recipient': recipient, 'amount': amount, 'signature': signature})
                        if response.status_code == 400 or response.status_code == 500:
                            print('Transaction declined, needs resolving')
                            return False
                        if response.status_code == 409:
                            self.resolve_conflicts = True
                    except requests.exceptions.ConnectionError:
                        continue
            return True
        return False

    def add_block(self, block):
        transactions = [Transaction(
            tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in block['transactions']]
        proof_is_valid = Verification.valid_proof(
            transactions[:-1], block['previous_hash'], block['proof'])
        hashes_match = hash_block(self.chain[-1]) == block['previous_hash']
        if not proof_is_valid or not hashes_match:
            return False
        converted_block = Block(
            block['index'], block['previous_hash'], transactions, block['proof'], block['timestamp'])
        self.__chain.append(converted_block)
        stored_transactions = self.__open_transactions[:]
        for itx in block['transactions']:
            for opentx in stored_transactions:
                if opentx.sender == itx['sender'] and opentx.recipient == itx['recipient'] and opentx.amount == itx['amount'] and opentx.signature == itx['signature']:
                    try:
                        self.__open_transactions.remove(opentx)
                    except ValueError:
                        print('Item already removed')

        self.save_data()
        return True

    def resolve(self):
        winner_chain = self.chain
        replace = False
        for node in self.__peer_nodes:
            url = 'http://{}'.format(node)
            try:
                response = requests.get(url)
                node_chain = response.json()
                node_chain = [Block(block['index'], block['previous_hash'], [Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in block['transactions']],
                                    block['proof'], block['timestamp']) for block in node_chain]
                #node_chain.transactions = [Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in node_chain.transactions]
                node_chain_length = len(node_chain)
                local_chain_length = len(winner_chain)
                if node_chain_length > local_chain_length and Verification.verify_chain(node_chain):
                    winner_chain = node_chain
                    replace = True
            except requests.exceptions.ConnectionError:
                continue

            self.resolve_conflicts = False
            self.chain = winner_chain
            if replace:
                self.__open_transactions = []
            self.save_data()
            return replace

    def mine_block(self):

        if self.hosting_node == None:
            return None
        last_block = self.__chain[-1]
        hashed_block = hash_block(last_block)
        proof = self.proof_of_work()
        print("my id is:")
        print(self.hosting_node)
        reward_transaction = Transaction('MINING', self.hosting_node, '', MINING_REWARD)

        copied_transactions = self.__open_transactions[:]
        for tx in copied_transactions:
            if not Wallet.verify_transaction(tx):
                return None
        copied_transactions.append(reward_transaction)
        block = Block(len(self.__chain), hashed_block, copied_transactions, proof)

        self.__chain.append(block)
        self.__open_transactions = []
        self.save_data()
        for node in self.__peer_nodes:
            print('trying ' + node)
            url = 'http://{}/broadcast-block'.format(node)
            converted_block = block.__dict__.copy()
            converted_block['transactions'] = [tx.__dict__ for tx in converted_block['transactions']]
            try:
                response = requests.post(url, json={"block": converted_block})
                if response.status_code == 400 or response.status_code == 500:
                    print("Problem with broadcasting mined block to peer nodes")
                if response.status_code == 409:
                    self.resolve_conflicts=True
            except requests.exceptions.ConnectionError:
                continue
        return block

    def calculate_balance(self, mode, participant):
        if mode=='sender':
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


    def add_peer_node(self, node):
        """
        Adds a new node to the peer node network
        Arguments :
            :node: the node url that should be added
        """
        self.__peer_nodes.add(node)
        self.save_data()

    def remove_peer_node(self, node):
        """
        Removed node from the peer node network
        Arguments :
            :node: the node url that should be removed
        """
        self.__peer_nodes.discard(node)
        self.save_data()

    def get_peer_nodes(self):
        """returns a list of all peer nodes"""
        return list(self.__peer_nodes)








