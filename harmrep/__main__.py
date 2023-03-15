"""This module calls the class App to start the project"""
import argparse

from .app import App

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--mode", required=True)
    parser.add_argument("-e", "--encoding", required=True)
    parser.add_argument("-n", "--run_name", required=False)
    parser.add_argument("-p", "--epochs", required=False)

    args = parser.parse_args()

    App.run(args.mode, args.encoding, args.run_name, args.epochs)
