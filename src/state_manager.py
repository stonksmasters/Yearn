import logging

# Configure logging (Pyodide-compatible)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.handlers = [console_handler]
logger.info("Initializing state_manager.py")

class GameState:
    def enter(self, game):
        """Called when entering the state."""
        pass

    def exit(self, game):
        """Called when exiting the state."""
        pass

    def update(self, game, dt):
        """Update logic for the state."""
        pass

class StartMenuState(GameState):
    def enter(self, game):
        game.ui.show_start_menu = True
        logger.info("Entered StartMenuState")

    def exit(self, game):
        game.ui.show_start_menu = False
        logger.info("Exited StartMenuState")

    def update(self, game, dt):
        # UI rendering handled by Renderer
        pass

class PlayingState(GameState):
    def enter(self, game):
        logger.info("Entered PlayingState")

    def exit(self, game):
        logger.info("Exited PlayingState")

    def update(self, game, dt):
        game.update(dt)
        logger.debug("Updated PlayingState")

class PausedState(GameState):
    def enter(self, game):
        game.ui.show_pause_menu = True
        logger.info("Entered PausedState")

    def exit(self, game):
        game.ui.show_pause_menu = False
        logger.info("Exited PausedState")

    def update(self, game, dt):
        # UI rendering handled by Renderer
        pass

class GameOverState(GameState):
    def enter(self, game):
        game.ui.game_over = True
        logger.info("Entered GameOverState")

    def exit(self, game):
        game.ui.game_over = False
        logger.info("Exited GameOverState")

    def update(self, game, dt):
        # UI rendering handled by Renderer
        pass

class PostDayUpgradesState(GameState):
    def enter(self, game):
        game.ui.show_post_day_upgrades = True
        logger.info("Entered PostDayUpgradesState")

    def exit(self, game):
        game.ui.show_post_day_upgrades = False
        logger.info("Exited PostDayUpgradesState")

    def update(self, game, dt):
        # UI rendering handled by Renderer
        pass

class StateManager:
    def __init__(self):
        self.states = {
            "start_menu": StartMenuState(),
            "playing": PlayingState(),
            "paused": PausedState(),
            "game_over": GameOverState(),
            "post_day_upgrades": PostDayUpgradesState()
        }
        self.current_state = "start_menu"
        logger.info("StateManager initialized with start_menu state")

    def set_state(self, state_name, game):
        """Transition to a new state."""
        if state_name not in self.states:
            logger.error(f"Invalid state: {state_name}")
            return
        logger.info(f"Transitioning from {self.current_state} to {state_name}")
        self.states[self.current_state].exit(game)
        self.current_state = state_name
        self.states[state_name].enter(game)

    def update(self, game, dt):
        """Update the current state."""
        self.states[self.current_state].update(game, dt)