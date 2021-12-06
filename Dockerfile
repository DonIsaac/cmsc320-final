# Inspired by https://github.com/cmsc320/docker/blob/main/Dockerfile
FROM jupyter/scipy-notebook

USER root
WORKDIR /home/$NB_USER

RUN apt-get update && apt-get install -y less make man git curl

# Install some packages with conda, then fix file perms
RUN conda install --quiet --yes \
  'html5lib' \
  'lxml' \
  'nltk' && \
  conda clean --all -f -y && \
  fix-permissions "${CONDA_DIR}" && \
  fix-permissions "/home/${NB_USER}"

USER $NB_UID
WORKDIR $HOME/notebooks

COPY --chown=${NB_UID} requirements.txt .
# RUN conda create --name env --file requirements.txt

# # Set up virtual environment
RUN python3 -m venv env
RUN source env/bin/activate

# # Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy over source after installing dependencies
COPY --chown=${NB_UID} . .

EXPOSE 8888
