import argparse
from pathlib import Path

from .config import load_config
from .data import download_weather, make_demo_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="changchun-air", description="PM2.5 event-warning research pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo-data", help="Generate clearly labelled synthetic demonstration data")
    demo.add_argument("--output", type=Path, default=Path("data/demo/air_quality.csv"))
    demo.add_argument("--years", type=int, default=3)
    demo.add_argument("--seed", type=int, default=42)

    weather = subparsers.add_parser("download-weather", help="Download Open-Meteo historical hourly weather")
    weather.add_argument("--output", type=Path, required=True)
    weather.add_argument("--start", required=True)
    weather.add_argument("--end", required=True)
    weather.add_argument("--latitude", type=float, default=43.88)
    weather.add_argument("--longitude", type=float, default=125.35)

    run = subparsers.add_parser("run", help="Run cleaning, analysis, training and reporting")
    run.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    run.add_argument("--air", type=Path, required=True)
    run.add_argument("--weather", type=Path)
    run.add_argument("--output", type=Path, default=Path("artifacts/run"))

    report = subparsers.add_parser("report", help="Regenerate a report from saved results")
    report.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "demo-data":
        frame = make_demo_data(args.output, args.years, args.seed)
        print(f"Generated {len(frame)} synthetic hourly rows: {args.output}")
    elif args.command == "download-weather":
        frame = download_weather(args.output, args.start, args.end, args.latitude, args.longitude)
        print(f"Downloaded {len(frame)} hourly weather rows: {args.output}")
    elif args.command == "run":
        from .pipeline import run_pipeline
        result = run_pipeline(args.config, args.air, args.weather, args.output)
        print(f"Report: {result['report']}")
    elif args.command == "report":
        from .reporting import generate_report
        print(f"Report: {generate_report(args.output)}")


if __name__ == "__main__":
    main()
