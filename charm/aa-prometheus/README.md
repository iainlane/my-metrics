# Metrics

Generate some metrics and set up a grafana.

## What you need to do

```
juju deploy --force ./bundle.yaml
```

The `--force` is needed because the prometheus charm doesn't support bionic, but the `aa-prometheus` charm requires it. It seems to work OK.

Wait for a bit until `juju status` says it's all OK, and then:

```
juju run-action --wait grafana/0 get-admin-password
```

Visit `http://<grafana IP>:3000` and log in with `admin` and that password. Then you can get on with setting up dashboards.

Take a look at `http://<prometheus IP>:9090` to see the metrics that you can graph.

## Exposing it properly

I've got a separate nginx proxy to do SSL termination - the above URLs are not open to the world. SSH into the `grafana` unit and add a static IP, and then add this to the proxy.

This bit sucks and it would be better if it could be more automated.