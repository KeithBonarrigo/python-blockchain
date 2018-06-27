from utility import hash_util
from wallet import Wallet

class Verification:

    @classmethod
    def verify_chain(cls, blockchain):
    #def verify_chain(self, blockchain):
        """ Verify the current blockchain and return True if it's valid, False otherwise."""
        for (index, block) in enumerate(blockchain):
            if index == 0:
                continue
            # if block['previous_hash'] != hash_util.hash_block(blockchain[index-1]):
            if block.previous_hash != hash_util.hash_block(blockchain[index - 1]):
                return False
            # if not valid_proof(block['transactions'][:-1], block['previous_hash'], block['proof']):
            if not cls.valid_proof(block.transactions[:-1], block.previous_hash, block.proof):
                print('proof of work is invalid')
                return False
        return True

    @staticmethod
    def valid_proof(transactions, last_hash, proof):
        # guess = (str(transactions) + str(last_hash) + str(proof)).encode()
        guess = (str([tx.to_ordered_dict() for tx in transactions]) + str(last_hash) + str(proof)).encode()
        guess_hash = hash_util.hash_string_256(guess)
        print(guess_hash)
        return guess_hash[0:2] == "00"

    @staticmethod
    def verify_transaction(transaction, get_balance, checkFunds=True):
        # sender_balance = get_balance(transaction['sender'])
        sender_balance = get_balance()
        #print("sender balance is " + str(sender_balance))
        # return sender_balance >= transaction['amount']
        if checkFunds:
            return sender_balance >= transaction.amount and Wallet.verify_transaction(transaction)
        else:
            return Wallet.verify_transaction(transaction)

    @classmethod
    def verify_transactions(cls, open_transactions, get_balance):
        is_valid = True
        for tx in open_transactions:
            if cls.verify_transaction(tx, get_balance, False):
                return True
            else:
                return False
        return is_valid