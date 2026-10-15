from dify_plugin import Plugin, DifyPluginEnv
from dify_plugin.core.trigger_factory import TriggerFactory


def _allow_tool_dynamic_select() -> None:
    """Tool plugins are not triggers. The SDK lookup raises before it can fall back."""
    original = TriggerFactory.get_trigger_event_handler_safely

    def get_trigger_event_handler_safely(self, provider_name, event, runtime):
        try:
            return original(self, provider_name, event, runtime)
        except ValueError:
            return None

    TriggerFactory.get_trigger_event_handler_safely = get_trigger_event_handler_safely


_allow_tool_dynamic_select()

plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=120))

if __name__ == "__main__":
    plugin.run()
