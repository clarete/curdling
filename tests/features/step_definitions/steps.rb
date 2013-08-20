require 'open3'
require 'fileutils'

# This is just an alias to access the fixtures of our features
fixture = lambda { |*p|
  File.absolute_path(File.join(File.dirname(__FILE__), "..", "fixtures", *p))
}


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
