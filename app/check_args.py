def check_args(args):
    for arg in args:
        if (len(arg.split()) > 1 ):
            print('not valid arguments')
            return 'not valid'
