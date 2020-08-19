#!/usr/bin/env bash

################################################################################
############# Deploy Container to DockerHub @admiralawkbar #####################
################################################################################

# NOTES: This script is used to upload a Dockerfile to DockerHub
# under the GitHub organization
# Its based on being built from a GitHub Action, but could be easily updated
# To be ran in a different medium.
#
# PRE-Requirements:
# - Dockerfile
# - System with Docker installed
# - Global variables met

###########
# Globals #
###########
GITHUB_WORKSPACE="${GITHUB_WORKSPACE}" # GitHub Workspace
DOCKER_USERNAME="${DOCKER_USERNAME}"   # Username to login to DockerHub
DOCKER_PASSWORD="${DOCKER_PASSWORD}"   # Password to login to DockerHub
GPR_USERNAME="${GPR_USERNAME}"         # Username to login to GitHub package registry
GPR_TOKEN="${GPR_TOKEN}"               # Password to login to GitHub package registry
REGISTRY="${REGISTRY}"                 # What registry to upload | <GPR> or <Docker>
IMAGE_REPO="${IMAGE_REPO}"             # Image repo to upload the image
IMAGE_VERSION="${IMAGE_VERSION}"       # Version to tag the image
DOCKERFILE_PATH="${DOCKERFILE_PATH}"   # Path to the Dockerfile to be uploaded
MAJOR_TAG=''                           # Major tag version if we need to update it
UPDATE_MAJOR_TAG=0                     # Flag to deploy the major tag version as well

#########################
# Source Function Files #
#########################
# shellcheck source=/dev/null
source "${GITHUB_WORKSPACE}/lib/log.sh" # Source the function script(s)

################################################################################
############################ FUNCTIONS BELOW ###################################
################################################################################
################################################################################
#### Function Header ###########################################################
Header() {
  info "-------------------------------------------------------"
  info "---- GitHub Actions Upload image to [${REGISTRY}] ----"
  info "-------------------------------------------------------"
}
################################################################################
#### Function ValidateInput ####################################################
ValidateInput() {
  # Need to validate we have the basic variables
  ################
  # Print header #
  ################
  info "----------------------------------------------"
  info "Gathering variables..."
  info "----------------------------------------------"

  #############################
  # Validate GITHUB_WORKSPACE #
  #############################
  if [ -z "${GITHUB_WORKSPACE}" ]; then
    error "Failed to get [GITHUB_WORKSPACE]!"
    fatal "[${GITHUB_WORKSPACE}]"
  else
    info "Successfully found:${F[W]}[GITHUB_WORKSPACE]${F[B]}, value:${F[W]}[${GITHUB_WORKSPACE}]"
  fi

  #####################
  # Validate REGISTRY #
  #####################
  if [ -z "${REGISTRY}" ]; then
    error "Failed to get [REGISTRY]!"
    fatal "[${REGISTRY}]"
  else
    info "Successfully found:${F[W]}[REGISTRY]${F[B]}, value:${F[W]}[${REGISTRY}]"
  fi

  #####################################################
  # See if we need values for GitHub package Registry #
  #####################################################
  if [[ ${REGISTRY} == "GPR" ]]; then
    #########################
    # Validate GPR_USERNAME #
    #########################
    if [ -z "${GPR_USERNAME}" ]; then
      error "Failed to get [GPR_USERNAME]!"
      fatal "[${GPR_USERNAME}]"
    else
      info "Successfully found:${F[W]}[GPR_USERNAME]${F[B]}, value:${F[W]}[${GPR_USERNAME}]"
    fi

    ######################
    # Validate GPR_TOKEN #
    ######################
    if [ -z "${GPR_TOKEN}" ]; then
      error "Failed to get [GPR_TOKEN]!"
      fatal "[${GPR_TOKEN}]"
    else
      info "Successfully found:${F[W]}[GPR_TOKEN]${F[B]}, value:${F[W]}[********]"
    fi
  ########################################
  # See if we need values for Ducker hub #
  ########################################
  elif [[ ${REGISTRY} == "Docker" ]]; then
    ############################
    # Validate DOCKER_USERNAME #
    ############################
    if [ -z "${DOCKER_USERNAME}" ]; then
      error "Failed to get [DOCKER_USERNAME]!"
      fatal "[${DOCKER_USERNAME}]"
    else
      info "Successfully found:${F[W]}[DOCKER_USERNAME]${F[B]}, value:${F[W]}[${DOCKER_USERNAME}]"
    fi

    ############################
    # Validate DOCKER_PASSWORD #
    ############################
    if [ -z "${DOCKER_PASSWORD}" ]; then
      error "Failed to get [DOCKER_PASSWORD]!"
      fatal "[${DOCKER_PASSWORD}]"
    else
      info "Successfully found:${F[W]}[DOCKER_PASSWORD]${F[B]}, value:${F[B]}[********]"
    fi
  ###########################################
  # We were not passed a registry to update #
  ###########################################
  else
    error "Failed to find a valid registry!"
    fatal "Registry:[${REGISTRY}]"
  fi

  #######################
  # Validate IMAGE_REPO #
  #######################
  if [ -z "${IMAGE_REPO}" ]; then
    error "Failed to get [IMAGE_REPO]!"
    fatal "[${IMAGE_REPO}]"
  else
    info "Successfully found:${F[W]}[IMAGE_REPO]${F[B]}, value:${F[W]}[${IMAGE_REPO}]"
    ###############################################
    # Need to see if GPR registry and update name #
    ###############################################
    if [[ ${REGISTRY} == "GPR" ]]; then
      NAME="docker.pkg.github.com/${IMAGE_REPO}/super-linter"
      IMAGE_REPO="${NAME}"
      info "Updated [IMAGE_REPO] to:[${IMAGE_REPO}] for GPR"
    fi
  fi

  ##########################
  # Validate IMAGE_VERSION #
  ##########################
  if [ -z "${IMAGE_VERSION}" ]; then
    warn "Failed to get [IMAGE_VERSION]!"
    info "Pulling from Branch Name..."
    ##############################
    # Get the name of the branch #
    ##############################
    BRANCH_NAME=$(git -C "${GITHUB_WORKSPACE}" branch --contains "${GITHUB_SHA}" | awk '{print ${2}}' 2>&1)

    #######################
    # Load the error code #
    #######################
    ERROR_CODE=$?

    ##############################
    # Check the shell for errors #
    ##############################
    if [ ${ERROR_CODE} -ne 0 ]; then
      error "Failed to get branch name!"
      fatal "[${BRANCH_NAME}]"
    fi

    ##################################
    # Remove non alpha-numeric chars #
    ##################################
    BRANCH_NAME=$(echo "${BRANCH_NAME}" | tr -cd '[:alnum:]')

    ############################################
    # Set the IMAGE_VERSION to the BRANCH_NAME #
    ############################################
    IMAGE_VERSION="${BRANCH_NAME}"
    info "Tag:[${IMAGE_VERSION}]"
  else
    info "Successfully found:${F[W]}[IMAGE_VERSION]${F[B]}, value:${F[W]}[${IMAGE_VERSION}]"
  fi

  ##################################
  # Set regex for getting tag info #
  ##################################
  REGEX='(v[0-9]+\.[0-9]+\.[0-9]+)' # Matches 'v1.2.3'

  ######################################################################
  # Check if this is a latest to a versioned release at create new tag #
  ######################################################################
  if [[ ${IMAGE_VERSION} =~ ${REGEX} ]]; then
    # Need to get the major version, and set flag to update

    #####################
    # Set the major tag #
    #####################
    MAJOR_TAG=$(echo "${IMAGE_VERSION}" | cut -d '.' -f1)

    ###################################
    # Set flag for updating major tag #
    ###################################
    UPDATE_MAJOR_TAG=1

    info "- Also deploying a major tag of:[${MAJOR_TAG}]"
  fi

  ############################
  # Validate DOCKERFILE_PATH #
  ############################
  if [ -z "${DOCKERFILE_PATH}" ]; then
    error "Failed to get [DOCKERFILE_PATH]!"
    fatal "[${DOCKERFILE_PATH}]"
  else
    info "Successfully found:${F[W]}[DOCKERFILE_PATH]${F[B]}, value:${F[W]}[${DOCKERFILE_PATH}]"
  fi
}
################################################################################
#### Function Authenticate #####################################################
Authenticate() {
  ################
  # Pull in Vars #
  ################
  USERNAME="${1}" # Name to auth with
  PASSWORD="${2}" # Password to auth with
  URL="${3}"      # Url to auth towards
  NAME="${4}"     # name of the service

  ################
  # Print header #
  ################
  info "----------------------------------------------"
  info "Login to ${NAME}..."
  info "----------------------------------------------"

  ###################
  # Auth to service #
  ###################
  LOGIN_CMD=$(docker login "${URL}" --username "${USERNAME}" --password "${PASSWORD}" 2>&1)

  #######################
  # Load the error code #
  #######################
  ERROR_CODE=$?

  ##############################
  # Check the shell for errors #
  ##############################
  if [ ${ERROR_CODE} -ne 0 ]; then
    # ERROR
    error "Failed to authenticate to ${NAME}!"
    fatal "[${LOGIN_CMD}]"
  else
    # SUCCESS
    info "Successfully authenticated to ${F[C]}${NAME}${F[B]}!"
  fi
}
################################################################################
#### Function BuildImage #######################################################
BuildImage() {
  ################
  # Print header #
  ################
  info "----------------------------------------------"
  info "Building the DockerFile image..."
  info "----------------------------------------------"

  ################################
  # Validate the DOCKERFILE_PATH #
  ################################
  if [ ! -f "${DOCKERFILE_PATH}" ]; then
    # No file found
    error "failed to find Dockerfile at:[${DOCKERFILE_PATH}]"
    error "Please make sure you give full path!"
    fatal "Example:[/configs/Dockerfile] or [Dockerfile] if at root directory"
  fi

  ###################
  # Build the image #
  ###################
  docker build --no-cache -t "${IMAGE_REPO}:${IMAGE_VERSION}" -f "${DOCKERFILE_PATH}" . 2>&1

  #######################
  # Load the error code #
  #######################
  ERROR_CODE=$?

  ##############################
  # Check the shell for errors #
  ##############################
  if [ ${ERROR_CODE} -ne 0 ]; then
    # ERROR
    fatal "failed to [build] Dockerfile!"
  else
    # SUCCESS
    info "Successfully Built image!"
  fi

  ########################################################
  # Need to see if we need to tag a major update as well #
  ########################################################
  if [ ${UPDATE_MAJOR_TAG} -eq 1 ]; then
    # Tag the image with the major tag as well
    docker build -t "${IMAGE_REPO}:${MAJOR_TAG}" -f "${DOCKERFILE_PATH}" . 2>&1

    #######################
    # Load the error code #
    #######################
    ERROR_CODE=$?

    ##############################
    # Check the shell for errors #
    ##############################
    if [ ${ERROR_CODE} -ne 0 ]; then
      # ERROR
      fatal "failed to [tag] Dockerfile!"
    else
      # SUCCESS
      info "Successfully tagged image!"
    fi
  fi
}
################################################################################
#### Function UploadImage ######################################################
UploadImage() {
  ################
  # Print header #
  ################
  info "----------------------------------------------"
  info "Uploading the DockerFile image to ${REGISTRY}..."
  info "----------------------------------------------"

  ############################################
  # Upload the docker image that was created #
  ############################################
  docker push "${IMAGE_REPO}:${IMAGE_VERSION}" 2>&1

  #######################
  # Load the error code #
  #######################
  ERROR_CODE=$?

  ##############################
  # Check the shell for errors #
  ##############################
  if [ ${ERROR_CODE} -ne 0 ]; then
    # ERROR
    fatal "failed to [upload] Dockerfile!"
  else
    # SUCCESS
    info "Successfully Uploaded Docker image:${F[W]}[${IMAGE_VERSION}]${F[B]} to ${F[C]}${REGISTRY}${F[B]}!"
  fi

  #########################
  # Get Image information #
  #########################
  IFS=$'\n' # Set the delimit to newline
  GET_INFO_CMD=$(docker images | grep "${IMAGE_REPO}" | grep "${IMAGE_VERSION}" 2>&1)

  #######################
  # Load the error code #
  #######################
  ERROR_CODE=$?

  ##############################
  # Check the shell for errors #
  ##############################
  if [ ${ERROR_CODE} -ne 0 ]; then
    # ERROR
    error "Failed to get information about built Image!"
    fatal "[${GET_INFO_CMD}]"
  else
    ################
    # Get the data #
    ################
    REPO=$(echo "${GET_INFO_CMD}" | awk '{print ${1}}')
    TAG=$(echo "${GET_INFO_CMD}" | awk '{print ${2}}')
    IMAGE_ID=$(echo "${GET_INFO_CMD}" | awk '{print ${3}}')
    SIZE="${GET_INFO_CMD##* }"

    ###################
    # Print the goods #
    ###################
    info "----------------------------------------------"
    info "Docker Image Details:"
    info "Repository:[${REPO}]"
    info "Tag:[${TAG}]"
    info "Image_ID:[${IMAGE_ID}]"
    info "Size:[${SIZE}]"
    info "----------------------------------------------"
  fi

  ###############################################################
  # Check if we need to upload the major tagged version as well #
  ###############################################################
  if [ ${UPDATE_MAJOR_TAG} -eq 1 ]; then
    ############################################
    # Upload the docker image that was created #
    ############################################
    docker push "${IMAGE_REPO}:${MAJOR_TAG}" 2>&1

    #######################
    # Load the error code #
    #######################
    ERROR_CODE=$?

    ##############################
    # Check the shell for errors #
    ##############################
    if [ ${ERROR_CODE} -ne 0 ]; then
      # ERROR
      fatal "failed to [upload] MAJOR_TAG:[${MAJOR_TAG}] Dockerfile!"
    else
      # SUCCESS
      info "Successfully Uploaded TAG:${F[W]}[${MAJOR_TAG}]${F[B]} of Docker image to ${F[C]}${REGISTRY}${F[B]}!"
    fi
  fi
}
################################################################################
#### Function Footer ###########################################################
Footer() {
  info "-------------------------------------------------------"
  info "The step has completed"
  info "-------------------------------------------------------"
}
################################################################################
################################## MAIN ########################################
################################################################################

##########
# Header #
##########
Header

##################
# Validate Input #
##################
ValidateInput

###################
# Build the image #
###################
BuildImage

######################
# Login to DockerHub #
######################
if [[ ${REGISTRY} == "Docker" ]]; then
  # Authenticate "Username" "Password" "Url" "Name"
  Authenticate "${DOCKER_USERNAME}" "${DOCKER_PASSWORD}" "" "Dockerhub"

####################################
# Login to GitHub Package Registry #
####################################
elif [[ ${REGISTRY} == "GPR" ]]; then
  # Authenticate "Username" "Password" "Url" "Name"
  Authenticate "${GPR_USERNAME}" "${GPR_TOKEN}" "https://docker.pkg.github.com" "GitHub Package Registry"

else
  #########
  # ERROR #
  #########
  error "Registry not set correctly!"
  fatal "Registry:[${REGISTRY}]"
fi

####################
# Upload the image #
####################
UploadImage

##########
# Footer #
##########
Footer
