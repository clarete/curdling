require 'open3'
require 'fileutils'
require 'httpclient'


# -- Helpers --


# This is just an alias to access the fixtures of our features
fixture = lambda { |*p|
  File.absolute_path(File.join(File.dirname(__FILE__), "..", "fixtures", *p))
}


# -- Hooks --


# Removing the fixtures created temporarily
After do |scenario|
  @current_directory = nil
  Dir.entries(fixture.call).each {|entry|
    FileUtils.rm_rf(fixture.call entry) unless entry.start_with? "."
  }
end

# -- Steps --


Given(/^that I have a project called "(.*?)"$/) do |arg1|
  # Changes the current path of the test to the arg1
  @current_directory = (FileUtils.mkdir_p fixture.call(arg1))[0]
end

Given(/^a file called "(.*?)" with:$/) do |arg1, string|
  # Full path for the file name
  file = fixture.call(arg1)

  # Create a new file with the content received in "string"
  Dir.chdir(@current_directory) { |path|
    File.open(file, 'w') { |f|
      f.write(string)
    }
  }
end

When(/^I run "(.*?)"$/) do |arg1|
  pkgdir = Dir.pwd
  output = ''

  Dir.chdir(@current_directory) { |path|
    Open3.popen3({"PYTHONPATH" => pkgdir}, arg1) { |stdin, stdout, stderr|
      output += stdout.read
      output += stderr.read
    }
  }

  # Reset the output
  @output = output.strip
end

Then(/^I should see:$/) do |string|
  begin
    @output.should be_eql string
  rescue
    puts @output
    raise
  end
end

Then(/^I ensure that "(.*?)" is installed$/) do |arg1|
  (`pip freeze`.include? arg1).should be_true
end

Given(/^I run the server with "(.*?)"$/) do |cmd|
  @server_pid = spawn({"PYTHONPATH" => Dir.pwd}, cmd,
                      :pgroup=>true,
                      :chdir=>@current_directory,
                      :err=>:out, :out=>STDOUT)

  # Making sure the server has enough time to be spawn
  url = "http://localhost:8001"
  client = HTTPClient.new
  while not (begin client.get_content(url) rescue false end)
      sleep 1
  end
end

Given(/^I shutdown the server$/) do
  Process.kill("INT", -@server_pid)
  Process.wait
end
