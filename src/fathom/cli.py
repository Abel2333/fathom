from fathom.config.logging import LoggerSetup, get_logger


def main():
    """Main entry point for the Fathom CLI."""
    # Initialize logging
    LoggerSetup.setup_logging()

    logger = get_logger(__name__)
    logger.info("Starting Fathom Deep Research Agent")

    print("Hello from fathom!")

    logger.info("Fathom session completed")


if __name__ == "__main__":
    main()
