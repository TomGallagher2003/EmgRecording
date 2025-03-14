from config import Config
from recording import EmgSession


if __name__ == "__main__":

    print("Beginning data collection")
    session = EmgSession()
    session.start()

    session.iterate_recordings(Config.IMAGE_SOURCE_PATH, Config.DATA_DESTINATION_PATH)

    session.finish()



