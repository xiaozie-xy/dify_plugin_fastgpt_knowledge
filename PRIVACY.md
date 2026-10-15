## Privacy Policy

This plugin sends the configured FastGPT API key, the runtime dataset ID, the search text, and the search settings to the FastGPT address you enter. It does not add another storage service.

### Data Collection

- The FastGPT API key is stored by Dify as a plugin credential.
- Each invocation sends the dataset ID, search text, and FastGPT searchTest parameters to that FastGPT address.
- The plugin process does not write queries or retrieved chunks to its own database.

### Data Usage

Retrieved chunks are returned to the Dify workflow that invoked the tool. The only external endpoint is the FastGPT API address configured in the plugin credentials. Cloud FastGPT is typically `https://cloud.fastgpt.cn`. A self-hosted deployment uses the address entered by the operator.

### Data Retention

The plugin does not retain request or response bodies after the tool invocation finishes. Credential storage and workflow logs follow the Dify instance where the plugin is installed.

### Contact

Maintainer: xiaozie-xy@foxmail.com

You can also open an issue at https://github.com/xiaozie-xy/dify_plugin_fastgpt_knowledge/issues.

Privacy questions about a local installation should also go to the operator of that Dify instance.
