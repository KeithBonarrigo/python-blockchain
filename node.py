from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from wallet import Wallet
from blockchain import Blockchain

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def get_node_ui():
    return send_from_directory('ui', 'node.html')

@app.route('/network', methods=['GET'])
def get_network_ui():
    return send_from_directory('ui', 'network.html')

@app.route('/wallet', methods=['POST'])
def create_keys():
    wallet.create_keys()
    if wallet.save_keys():
        global blockchain
        blockchain = Blockchain(wallet.public_key, port)
        response = {
            'public_key':wallet.public_key,
            'private_key':wallet.private_key,
            'funds': blockchain.get_balance()
        }

        return jsonify(response), 201
    else:
        response = {
            'message': 'Saving keys failed'
        }
        return jsonify(response), 500

@app.route('/wallet', methods=['GET'])
def load_keys():
    if wallet.load_keys():
        global blockchain
        blockchain = Blockchain(wallet.public_key, port)
        response = {
            'public_key': wallet.public_key,
            'private_key': wallet.private_key,
            'funds':blockchain.get_balance()
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'Loading keys failed'
        }
        return jsonify(response), 500

@app.route('/broadcast-block', methods=['POST'])
def broadcast_block():
    values = request.get_json()
    if not values:
        response = {"message": "No data found" }
        return jsonify(response), 400
    if 'block' not in values:
        response = {"message": "Missing required transaction data" }
        return jsonify(response), 400
    block = values['block']
    if block['index'] == blockchain.chain[-1].index + 1: #this is the next block in the chain as indicated by the index - go ahead and add it
        if blockchain.add_block(block):
            response = {'message': 'block added' }
            return jsonify(response), 201
        else:
            response = {'message': 'block seems invalid'}
            return jsonify(response), 409
    elif block['index'] > blockchain.chain[-1].index:
        response = {'message': 'blockchain differs from local blockchain'}
        blockchain.resolve_conflicts = True
        return jsonify(response), 200
    else:
        response = {'message':'blockchain seems to be shorter than local blockchain - block not added' }
        return jsonify(response), 409



@app.route('/broadcast-transaction', methods=['POST'])
def broadcast_transaction():
    values = request.get_json()

    if not values:
        response = {
            "message": "No data found"
        }
        return jsonify(response), 400
    required = ['sender', 'recipient', 'amount', 'signature']
    if not all(key in values for key in required):
        response = {
            "message": "Missing required transaction data"
        }
        return jsonify(response), 400
    success = blockchain.add_broadcast_transaction(values['recipient'], values['sender'], values['signature'], values['amount'], is_receiving=True)
    print("success is:")
    print(success)
    if success:
        response = {
            'message': 'added transaction',
            'transaction': {
                'sender': values['sender'],
                'recipient': values['recipient'],
                'amount': values['amount'],
                'signature': values['signature']
            }
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'unable to add transaction!'
        }
        return jsonify(response), 500


@app.route('/transaction', methods=['POST'])
def add_transaction():
    if wallet.public_key == None:
        response = {
            'message':'no wallet set up'
        }
        return jsonify(response), 400
    values = request.get_json()
    if not values:
        response = {
            'message': 'no data found'
        }
        return jsonify(response), 404
    required_fields = ['recipient', 'amount']
    if not all(field in values for field in required_fields):
        response = {
            'message': 'missing required data'
        }
        return jsonify(response), 400

    recipient = values['recipient']
    amount = values['amount']

    signature = wallet.sign_transaction(wallet.public_key, values['recipient'], values['amount'])
    success = blockchain.add_transaction(recipient, wallet.public_key, signature, amount)
    if success:
        response = {
            'message': 'added transaction',
            'transaction': {
                'sender': wallet.public_key,
                'recipient': recipient,
                'amount': amount,
                'signature':signature
            },
            'funds': blockchain.get_balance()
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'unable to add transaction'
        }
        return jsonify(response), 500


@app.route('/mine', methods=['POST'])
def mine():
    if blockchain.resolve_conflicts:
        response = {'message':'Resolve conflicts first - block not added'}
        return jsonify(response), 409
    block = blockchain.mine_block()
    if block != None:
        dict_block = block.__dict__.copy()
        dict_block['transactions'] = [tx.__dict__ for tx in dict_block['transactions']]
        response = {
            'message':'block added successfully',
            'block': dict_block,
            'funds': blockchain.get_balance()
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'adding a block failed',
            'wallet_set_up': wallet.public_key != None
        }
        return jsonify(response), 500

@app.route('/resolve-confilcts', methods=['POST'])
def resolve_conflicts():
    replaced = blockchain.resolve()
    if replaced:
        response = {
            'message': 'Chain was replaced'
        }
    else:
        response = {
            'message': 'Local chain kept'
        }
    return jsonify(response), 200

@app.route('/transactions', methods=['GET'])
def get_open_transactions():
    transactions = blockchain.get_open_transactions()
    dict_transactions = [tx.__dict__ for tx in transactions]
    return jsonify(dict_transactions), 200

@app.route('/chain', methods=['GET'])
def get_chain():
    chain_snapshot = blockchain.chain
    dict_chain = [block.__dict__.copy() for block in chain_snapshot]
    for dict_block in dict_chain:
        dict_block['transactions'] = [tx.__dict__ for tx in dict_block['transactions']]
    return jsonify(dict_chain), 200

@app.route('/balance', methods=['GET'])
def get_balance():
    balance = blockchain.get_balance()
    if balance != None:
        response = {
            'message': 'get balance worked',
            'funds': balance
        }
        return jsonify(response), 200
    else:
        response = {
            'message': 'get balance failed',
            'wallet_set_up': wallet.public_key != None
        }
        return jsonify(response), 500

@app.route('/nodes', methods=['GET'])
def get_nodes():
    nodes = blockchain.get_peer_nodes()
    response = {
        "all_nodes":nodes
    }
    return jsonify(response), 200

@app.route('/node', methods=['POST'])
def add_node():
    values = request.get_json()

    if not values:
        response = {
            'message': 'No data available'
        }
        return jsonify(response), 400
    if 'node' not in values:
        response = {
            'message': 'No node data available'
        }
        return jsonify(response), 400
    else:
        node = values['node']
        blockchain.add_peer_node(node)
        response = {
            'message':'Node added successfully',
            'all_nodes':blockchain.get_peer_nodes()
        }
        return jsonify(response), 200


@app.route('/node/<node_url>/', methods=['DELETE'])
def remove_node(node_url):
    #values = request.get_json()
    if node_url == '' or node_url == None:
        response = {
            'message': 'No data available'
        }
        return jsonify(response), 400
    else:
        blockchain.remove_peer_node(node_url)
        response = {
            'message': 'Node ' + node_url + 'deleted successfully',
            'all_nodes': blockchain.get_peer_nodes()
        }
        return jsonify(response), 200

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=5000)
    args = parser.parse_args()
    port = args.port
    wallet = Wallet(port)
    blockchain = Blockchain(wallet.public_key, port)
    app.run(host='127.0.0.1', port=port)
