#!/bin/bash

set -e
set -x

deploy_repo_pull="https://github.com/truchas/truchas_releases"
deploy_repo_push="git@github.com:truchas/truchas_releases.git"

if [[ $CI_COMMIT_TAG == "" ]]; then
    # Development version
    dest_dir="dev"
else
    # Release version
    dest_dir="release"
fi

version=$(<dist/version)

mkdir ~/.ssh
chmod 700 ~/.ssh
ssh-keyscan gitlab.com >> ~/.ssh/known_hosts
ssh-keyscan github.com >> ~/.ssh/known_hosts

eval "$(ssh-agent -s)"


D=`pwd`

mkdir $HOME/repos
cd $HOME/repos

git clone ${deploy_repo_pull} tarballs
cd tarballs/docs

python3 $D/ci/tarball_update_json.py ${dest_dir} ${version} ${CI_COMMIT_SHA}

git config user.name "Deploy"
git config user.email "noreply@deploy"
COMMIT_MESSAGE="Deploying on $(date "+%Y-%m-%d %H:%M:%S")"

git add .
git commit -m "${COMMIT_MESSAGE}"

git show HEAD -p --stat
dest_commit=$(git show HEAD -s --format=%H)

if [[ ${CI_COMMIT_REF_NAME} != "master" ]]; then
    # We only execute the rest on master
    echo "Not a master branch, not tagged, skipping..."
    exit 0
fi


set +x
if [[ "${SSH_PRIVATE_KEY_TARBALL}" == "" ]]; then
    echo "Note: SSH_PRIVATE_KEY_TARBALL is empty, skipping..."
    exit 0
fi
# Generate the private/public key pair using:
#
#     ssh-keygen -f deploy_key -N ""
#
# then set the $SSH_PRIVATE_KEY_TARBALL environment variable in the GitLab-CI
# to the base64 encoded private key (check the "Masked" check box for extra
# security):
#
#     cat deploy_key | base64 -w0
#
# and add the public key `deploy_key.pub` into the target git repository (with
# write permissions).

ssh-add <(echo "$SSH_PRIVATE_KEY_TARBALL" | base64 -d)
set -x


git push ${deploy_repo_push} master:master
echo "New commit pushed at:"
echo "https://github.com/truchas/truchas_releases/commit/${dest_commit}"
