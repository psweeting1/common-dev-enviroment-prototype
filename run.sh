export DC_CMD='docker compose'

# Best effort check that the script has been sourced.
# From https://stackoverflow.com/a/28776166

sourced=0  # Default: assume not sourced

# Check for Zsh: $ZSH_EVAL_CONTEXT contains ':file' if sourced
if [ -n "$ZSH_EVAL_CONTEXT" ]; then
  case $ZSH_EVAL_CONTEXT in *:file) sourced=1;; esac
# Check for KornShell: compare script path to ${.sh.file}
elif [ -n "$KSH_VERSION" ]; then
  [ "$(cd $(dirname -- $0) && pwd -P)/$(basename -- $0)" != "$(cd $(dirname -- ${.sh.file}) && pwd -P)/$(basename -- ${.sh.file})" ] && sourced=1
# Check for Bash: 'return' only works if sourced
elif [ -n "$BASH_VERSION" ]; then
  (return 0 2>/dev/null) && sourced=1
# Fallback for other shells: check if $0 is a known shell binary
else
  # Detects 'sh' and 'dash'; add more shell names if needed
  case ${0##*/} in sh|dash) sourced=1;; esac
fi

# If not sourced, warn the user and pause for 10 seconds
if test $sourced -eq 0; then
    echo -e "\e[36mIt looks like you have executed the script directly instead of sourcing it. This will cause problems due to unset environment variables afterwards. I'll give you 10 seconds to CTRL-C out before continuing...\e[0m"
    sleep 10
fi

command="$1"         # Get the first argument as the main command
subcommands="$2"     # Get the second argument as subcommands or flags

if [ "$command" = "up" ]
then
    echo -e "\e[36mBeginning UP\e[0m"  # Inform the user that the 'up' process is starting
    # Run Ruby script to check for updates, prepare config, update apps, and prepare docker-compose
    ruby logic.rb --check-for-update --prepare-config --update-apps --prepare-compose "${subcommands}" &&
    # Source the docker preparation script
    source scripts/docker_prepare.sh &&
    # Source the script to add shell aliases
    source scripts/add-aliases.sh &&
    # Run Ruby script to build images, provision commodities, and start apps
    ruby logic.rb --build-images --provision-commodities --start-apps "${subcommands}"

elif [ "$command" = "quickup" ]
then
    echo -e "\e[36mBeginning UP (Quick mode)\e[0m"  # Inform the user that 'quickup' is starting
    # Run Ruby script to check for updates and prepare docker-compose (skip config and app updates)
    ruby logic.rb --check-for-update --prepare-compose &&
    # Source the docker preparation script
    source scripts/docker_prepare.sh &&
    # Source the script to add shell aliases
    source scripts/add-aliases.sh &&
    # Run Ruby script to start apps only
    ruby logic.rb --start-apps

elif [ "$command" = "halt" ]
then
    echo -e "\e[36mBeginning HALT\e[0m"  # Notify user that halt is starting
    ruby logic.rb --prepare-compose &&    # Prepare docker-compose configuration
    source scripts/docker_prepare.sh &&   # Prepare Docker environment
    ruby logic.rb --stop-apps &&          # Stop all running apps/containers
    source scripts/docker_clean.sh &&     # Clean up Docker resources
    source scripts/add-aliases.sh &&      # Add shell aliases
    source scripts/remove-aliases.sh      # Remove shell aliases

elif [ "$command" = "reload" ]
then
    echo -e "\e[36mBeginning RELOAD\e[0m"  # Notify user that reload is starting
    ruby logic.rb --prepare-compose &&      # Prepare docker-compose configuration
    source scripts/docker_prepare.sh &&     # Prepare Docker environment
    ruby logic.rb --stop-apps --prepare-config --update-apps --prepare-compose "${subcommands}" &&  # Stop apps, update config and apps, re-prepare compose
    source scripts/docker_prepare.sh &&     # Prepare Docker environment again
    source scripts/add-aliases.sh &&        # Add shell aliases
    ruby logic.rb --build-images --provision-commodities --start-apps "${subcommands}"  # Build images, provision, and start apps

elif [ "$command" = "quickreload" ]
then
    echo -e "\e[36mBeginning RELOAD (Quick mode)\e[0m"  # Notify user that quick reload is starting
    ruby logic.rb --prepare-compose &&                   # Prepare docker-compose configuration
    source scripts/docker_prepare.sh &&                  # Prepare Docker environment
    ruby logic.rb --stop-apps --prepare-compose &&       # Stop apps and re-prepare compose
    source scripts/docker_prepare.sh &&                  # Prepare Docker environment again
    source scripts/add-aliases.sh &&                     # Add shell aliases
    ruby logic.rb --start-apps                           # Start apps only (no rebuild)

elif [ "$command" = "destroy" ]
then
    echo -e "\e[36mBeginning DESTROY\e[0m"  # Notify user that destroy is starting
    ruby logic.rb --prepare-compose &&       # Prepare docker-compose configuration
    source scripts/docker_prepare.sh &&      # Prepare Docker environment
    ruby logic.rb --reset &&                 # Reset environment (remove containers/images)
    export COMPOSE_FILE= &&                  # Unset COMPOSE_FILE environment variable
    export COMPOSE_PROJECT_NAME= &&          # Unset COMPOSE_PROJECT_NAME environment variable
    source scripts/add-aliases.sh &&         # Add shell aliases
    source scripts/remove-aliases.sh         # Remove shell aliases

elif [ "$command" = "repair" ]
then
    echo -e "\e[36mBeginning REPAIR\e[0m"   # Notify user that repair is starting
    ruby logic.rb prepare-compose &&         # Prepare docker-compose configuration
    source scripts/docker_prepare.sh &&      # Prepare Docker environment
    source scripts/add-aliases.sh            # Add shell aliases

else
    echo "Syntax:
   source run.sh [command] [flags]

   commands:
      up            configure, build and run all services; will pull updates
                    from services' git repos and rebuild images
      quickup       as per up, but without updating services' git repos or
                    rebuilding images
      halt          stop all containers
      reload        stop all containers, rebuild them, and restart them
                    (including commodity fragments)
      quickreload   as per reload, but without rebuilding images 
      destroy       stop and remove all containers, then remove all built
                    images and (optionally) reset common-dev-env configuration
      repair        set the docker-compose configuration to use *this* dev-env,
                    for users with several common-dev-env instances

   flags:
      -n, --nopull  for 'up' and 'reload' only; avoid docker hub ratelimiting 
                    by not checking for updates to FROM images used in 
                    Dockerfiles"
fi
