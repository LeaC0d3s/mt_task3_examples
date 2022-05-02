###############################################################################
# Language Modeling on Wikitext-2
#
# This file generates new sentences sampled from the language model.
#
###############################################################################
import argparse
import torch
import sys
import data

parser = argparse.ArgumentParser(description='PyTorch Wikitext-2 Language Model')
# Model parameters.
parser.add_argument('--input', type=str, action='store_true',
                    help="User defined Prompt for Text generation")
parser.add_argument('--data', type=str, default='./data/wikitext-2',
                    help='location of the data corpus')
parser.add_argument('--checkpoint', type=str, default='./model.pt',
                    help='model checkpoint to use')
parser.add_argument('--outf', type=str, default='generated.txt',
                    help='output file for generated text')
parser.add_argument('--words', type=int, default='1000',
                    help='number of words to generate')
parser.add_argument('--seed', type=int, default=1111,
                    help='random seed')
parser.add_argument('--cuda', action='store_true',
                    help='use CUDA')
parser.add_argument('--temperature', type=float, default=1.0,
                    help='temperature - higher will increase diversity')
parser.add_argument('--log-interval', type=int, default=100,
                    help='reporting interval')
args = parser.parse_args()

# Set the random seed manually for reproducibility.
torch.manual_seed(args.seed)
if torch.cuda.is_available():
    if not args.cuda:
        print("WARNING: You have a CUDA device, so you should probably run with --cuda.")

device = torch.device("cuda" if args.cuda else "cpu")

if args.temperature < 1e-3:
    parser.error("--temperature has to be greater or equal 1e-3.")

# loads trained model:
with open(args.checkpoint, 'rb') as f:
    model = torch.load(f, map_location=device)
model.eval()

# create instance of Corpus Class --> tokenized train, val and test file:
corpus = data.Corpus(args.data)
ntokens = len(corpus.dictionary)

is_transformer_model = hasattr(model, 'model_type') and model.model_type == 'Transformer'
if not is_transformer_model:
    hidden = model.init_hidden(1)

if args.input:
    print(type(args.input))

    idx_list = []
    input_t = args.input.split()
    len_t = len(input_t)
    c = 1
    print(input_t)
    for t in input_t:
        if t not in corpus.dictionary.word2idx:
            print(f"WARNING: the word -{t}- is not in the vocabulary!!")
            sys.exit()
        else:
            idx_list.append([corpus.dictionary.word2idx[t]])
    input = torch.tensor(idx_list, dtype=torch.long).to(device)
else:
    input = torch.randint(ntokens, (1, 1), dtype=torch.long).to(device)
    len_t = 0
    c = 0

with open(args.outf, 'w') as outf:
    with torch.no_grad():  # no tracking history
        for i in range(args.words-len_t):
            if is_transformer_model:
                output = model(input, False)
                word_weights = output[-1].squeeze().div(args.temperature).exp().cpu()
                word_idx = torch.multinomial(word_weights, 1)[0]
                word_tensor = torch.Tensor([[word_idx]]).long().to(device)
                input = torch.cat([input, word_tensor], 0)
            else:
                output, hidden = model(input, hidden)
                word_weights = output.squeeze().div(args.temperature).exp().cpu()
                word_idx = torch.multinomial(word_weights, 1)[0].squeeze()
                #print(word_idx)
                input.fill_(word_idx)

            word = corpus.dictionary.idx2word[word_idx]
            #print(word)
            if c > 0:
                for t in input_t:
                    outf.write(t + ' ')
                c -= 1
            outf.write(word + ('\n' if i % 20 == 19 else ' '))


            if i % args.log_interval == 0:
                print('| Generated {}/{} words'.format(i, args.words))
