# APM and Logs 

In these labs we will be working with some code for APM and Logs.

If your app is not running lets start it.

`cd ~/docker/ecommerce-workshop/deploy`

`docker-compose -f docker-compose-int.yml up -d` 

As always let's validate the deployment 

`docker ps -a` 

Now we will check the logs from each container 

`docker logs nginx` 

`docker logs store-frontend`

And so on 

We can now generate some traffic to the app 

`cd ~/docker/ecommerce-workshop/traffic`
 
`./generate-traffic.sh`

While in this directory let's be sure to check the logs 

`tail -f status.log`

Fyi the `status.log` file is created when you run the generate-traffic script 

We want to see how well the web page is or is not working.  We need to grab that url here's how to do that 

`curl http://169.254.169.254/latest/meta-data/public-hostname; echo`

This will print the fqdn of your ec2 instance.  Copy that and paste it into a web-browser ending in `:8080` 

It should look something like this 
`ec2-1-1-1-1.us-east-2.compute.amazonaws.com:8080` 

Now that we have seen the site and errors that are being generated let's resolve them using APM and Logs.

# Configure the agent for APM and Logs.  

Let's stop our running deployment.

`cd ~/docker/ecommerce-workshop/deploy`

`docker-compose -f docker-compose-int.yml down`

Let's review the deploy file 

`cat docker-compose-int.yml`

We should see that logs and APM are enabled already.  If your file does not contain this no worries I can help

```
version: '3'
services:
  agent:
    container_name: dd-agent
    image: "datadog/agent:latest"
    environment:
      - DD_SITE
      - DD_API_KEY
      - DD_HOSTNAME=bootcamp-lab
      - DD_TAGS="project:bootcamp"
      ## APM
      - DD_APM_ENABLED=true
      - DD_APM_NON_LOCAL_TRAFFIC=true
      ## LOGS
      - DD_LOGS_ENABLED=true
      - DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL=true
      - DD_CONTAINER_EXCLUDE_LOGS=name:agent
      - DD_DOCKER_LABELS_AS_TAGS={"my.custom.label.env":"env","my.custom.label.team":"team","my.custom.label.app":"app"}
```
Here is a link to an example file with everything we need [here](https://github.com/ScottMabeDDHQ/tps-bootcamp/blob/main/docker/deploy/docker-compose-instr.yml) it should also be in your deploy folder already.

# Instrument the store-frontend service 

The store-frontend service uses ruby 

Let's instapect the deploy file to learn more about the application.  

`cd ~/docker/ecommerce-workshop/deploy`

`cat docker-compose-int.yml`

You should see the following 

```
store-frontend:
    container_name: store-frontend
    environment:
      - DD_AGENT_HOST=agent
      - DD_LOGS_INJECTION=true
      - DD_PROFILING_ENABLED=true
      - DD_RUNTIME_METRICS_ENABLED=true #enable runtime metrics collection
      - DD_ENV=dev
      - DD_SERVICE=store-frontend
      - DD_VERSION=${STORE_VER}
      - RAILS_HIDE_STACKTRACE=false
      - ADS_PORT=${ADS_PORT}
      - DISCOUNTS_PORT=${DISCOUNTS_PORT}
      - ADS_ROUTE=${ADS_ROUTE}
      - DISCOUNTS_ROUTE=${DISCOUNTS_ROUTE}
    image: store-frontend:${STORE_VER}
    ports:
      - "3000:3000"
    depends_on:
      - agent
      - db
      - discounts
      - advertisements
    labels:
      com.datadoghq.ad.logs: '[{"source": "ruby", "service": "store-frontend"}]'
      my.custom.label.team: "web"
      my.custom.label.app: "spree"
```

You can also view the example if that is easier for you [here](https://github.com/ScottMabeDDHQ/tps-bootcamp/blob/40b3b250bd0d0f8d64f1daac60aaa80ca432fe0f/docker/deploy/docker-compose-instr.yml#L59)

We're going to instrument the app now 

`cd ~/docker/ecommerce-workshop/store-frontend/src/store-front`

Edit your `Gemfile` has this at the end of it as the last 4 lines

```
# Setup datadog ddtrace
gem 'ddtrace', require: 'ddtrace/auto_instrument'
gem 'dogstatsd-ruby', '~> 5.3'
gem 'google-protobuf', '~> 3.0'
```

If you need help please refer to this [link](https://github.com/ScottMabeDDHQ/tps-bootcamp/blob/c1d774b729ab4e95fd447a4f4b6de692df28db6e/docker/store-frontend/src/store-front/Gemfile#L59)

Up next we need to edit the `config.ru` file.  We will be adding the following 

```
# datadog - profiling
require 'ddtrace/profiling/preload'

run Rails.application
```
Here is the complete file for your [reference](https://github.com/ScottMabeDDHQ/tps-bootcamp/blob/main/docker/store-frontend/src/store-front/config.ru)


From here we need to create the `datadog.rb` file to allow tracing

`cd ~/docker/ecommerce-workshop/store-frontend/src/store-front/config/initializers`

create the `datadog.rb` file with vi or nano it should contain the following 

```
require 'datadog/statsd'
require 'ddtrace'

Datadog.configure do |c|
# This will activate auto-instrumentation for Rails
   c.use :rails, {'service_name': 'store-frontend', 'cache_service': 'store-frontend-cache', 'database_service': 'store-frontend-sqlite'}
# Make sure requests are also instrumented
   c.use :http, {'service_name': 'store-frontend'}
end
```
For reference a complete file is [here](https://github.com/ScottMabeDDHQ/tps-bootcamp/blob/main/docker/store-frontend/src/store-front/config/initializers/datadog.rb) 

Now we will configure ruby for logging 

`cd ~/docker/ecommerce-workshop/store-frontend/src/store-front/config/environments`

We must edit the `development.rb` file so that the end of the file looks like this 

```
# Add the log tags the way Datadog expects
  config.log_tags = {
    request_id: :request_id,
    dd: -> _ {
      correlation = Datadog.tracer.active_correlation
      {
        trace_id: correlation.trace_id.to_s,
        span_id:  correlation.span_id.to_s,
        env:      correlation.env.to_s,
        service:  correlation.service.to_s,
        version:  correlation.version.to_s
      }
    }
  }

  # Show the logging configuration on STDOUT
  config.show_log_configuration = true
end
```
Hint file for [reference](https://github.com/ScottMabeDDHQ/tps-bootcamp/blob/c1d774b729ab4e95fd447a4f4b6de692df28db6e/docker/store-frontend/src/store-front/config/environments/development.rb#L110)
