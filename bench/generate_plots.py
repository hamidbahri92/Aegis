from .cli import plot, sweep


def main():
    sweep('mwpm', [0.02,0.06], out_csv='bench_out/sweep.csv')
    try:
        plot('bench_out/sweep.csv')
    except Exception:
        pass
if __name__=='__main__':
    main()
