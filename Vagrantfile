Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-24.04"  # already downloaded, libvirt-compatible
  config.vm.hostname = "qt-dev"

  config.vm.provider "libvirt" do |v|
    v.default_prefix = "qt-dev"
    v.memory = 4096
    v.cpus   = 4
    v.management_network_mac = "52:54:00:AB:CD:EF"
  end

  # shared folder via rsync (no guest additions needed)
  config.vm.synced_folder ".", "/vagrant", type: "rsync",
    rsync__exclude: [".git/", ".vagrant/"]

  config.ssh.insert_key = true

  config.vm.provision "shell", path: "provision.sh"
end
