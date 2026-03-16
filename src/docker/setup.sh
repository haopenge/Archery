#!/bin/bash
set -euxo pipefail
ARCH="$(dpkg --print-architecture)"
#sqladvisor
if [[ "$ARCH" == "amd64" ]]; then
  curl -o sqladvisor -L https://github.com/LeoQuote/SQLAdvisor/releases/download/v2.1/sqladvisor-linux-amd64
  chmod +x sqladvisor
  curl -o sqlparser.tar.gz -L https://github.com/LeoQuote/SQLAdvisor/releases/download/v2.1/sqlparser-linux-amd64.tar.gz
  tar -xzvf sqlparser.tar.gz
  mv sqlparser /usr/local/sqlparser
  rm -rf sqlparser*
fi
#soar
SOAR_ARCH="amd64"
if [[ "$ARCH" == "arm64" ]]; then
  SOAR_ARCH="arm64"
fi
curl -L -q "https://github.com/XiaoMi/soar/releases/download/$SOAR_VERSION/soar.linux-$SOAR_ARCH" -o soar
chmod +x soar
#my2sql
if [[ "$ARCH" == "amd64" ]]; then
  curl -L -q https://raw.githubusercontent.com/liuhr/my2sql/master/releases/centOS_release_7.x/my2sql -o my2sql
  chmod +x my2sql
fi
#mongo
if [[ "$ARCH" == "amd64" ]]; then
  curl -L -q -o mongodb-linux-x86_64-rhel70-3.6.20.tgz https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-rhel70-3.6.20.tgz
  tar -xvf mongodb-linux-x86_64-rhel70-3.6.20.tgz
  mv /opt/mongodb-linux-x86_64-rhel70-3.6.20/bin/mongo /usr/local/bin/
  chmod +x /usr/local/bin/mongo
  rm -rf /opt/mongodb*
fi
#msodbc
curl -q -L https://packages.microsoft.com/keys/microsoft.asc -o /etc/apt/trusted.gpg.d/microsoft.asc
curl -q -L https://packages.microsoft.com/config/debian/11/prod.list -o /etc/apt/sources.list.d/mssql-release.list
apt-get update
if apt-cache show msodbcsql18 >/dev/null 2>&1; then
  ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev
fi
#oracle client
if [[ "$ARCH" == "amd64" ]]; then
  mkdir -p /opt/oracle
  cd /opt/oracle
  curl -q -L -o oracle-install.zip https://download.oracle.com/otn_software/linux/instantclient/1921000/instantclient-basic-linux.x64-19.21.0.0.0dbru.zip
  unzip oracle-install.zip
  apt-get install libaio1
  sh -c "echo /opt/oracle/instantclient_19_21 > /etc/ld.so.conf.d/oracle-instantclient.conf"
  ldconfig
  rm -rf oracle-install.zip
  cd -
fi
# mysql/percona client
curl -O https://repo.percona.com/apt/percona-release_latest.generic_all.deb
apt-get install -yq --no-install-recommends gnupg2 lsb-release ./percona-release_latest.generic_all.deb
apt-get update
percona-release setup -y ps-57
apt-get install -yq --no-install-recommends percona-toolkit
percona-release disable  ps-57
apt-get install -yq --no-install-recommends gcc libmariadb-dev libldap2-dev libsasl2-dev ldap-utils
# mysql 软链, 供 sqladvisor 使用
if [[ "$ARCH" == "amd64" ]]; then
  if [[ -f /usr/lib/x86_64-linux-gnu/libmariadb.so.3 && ! -f /usr/lib/x86_64-linux-gnu/libmysqlclient.so.18 ]]; then
    ln -s /usr/lib/x86_64-linux-gnu/libmariadb.so.3 /usr/lib/x86_64-linux-gnu/libmysqlclient.so.18
  fi
fi
apt-get clean
ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
echo $TZ > /etc/timezone
if [[ -f sqladvisor ]]; then chmod +x sqladvisor; fi
if [[ -f soar ]]; then chmod +x soar; fi
if [[ -f my2sql ]]; then chmod +x my2sql; fi
if [[ -f /usr/local/bin/mongo ]]; then chmod +x /usr/local/bin/mongo; fi
python3 -m venv venv4archery
